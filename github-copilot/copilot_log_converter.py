import json
import re
import sys
import os

def extract_file_path(text):
    """Extract file path from various formats."""
    # Pattern to match [](file:///path/to/file)
    match = re.search(r'\[\]\(file://([^)]+)\)', text)
    if match:
        return match.group(1)
    
    # Case 2: Just the uri
    match_uri = re.search(r'file://(\S+)', text)
    if match_uri:
        return match_uri.group(1)
        
    return text


def strip_ansi_codes(text):
    """
    Remove ANSI escape sequences (color codes, cursor control, etc.) from text.
    These are commonly found in terminal output.
    """
    # Pattern matches ANSI escape sequences: ESC [ ... final_byte
    # This covers color codes, cursor movement, and other control sequences
    ansi_pattern = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07')
    return ansi_pattern.sub('', text)


def truncate_output(text, head_lines=5, tail_lines=5):
    """
    Truncate long output, keeping the first `head_lines` and last `tail_lines`.
    Lines in between are replaced with an ellipsis indicator.
    """
    lines = text.split('\n')
    total_lines = len(lines)
    
    # If the output is short enough, return as-is
    if total_lines <= head_lines + tail_lines + 2:
        return text
    
    # Keep head and tail, add ellipsis in between
    head = lines[:head_lines]
    tail = lines[-tail_lines:] if tail_lines > 0 else []
    omitted = total_lines - head_lines - tail_lines
    
    result = head + [f'\n... ({omitted} lines omitted) ...\n'] + tail
    return '\n'.join(result)


def format_inline_reference(resp):
    """
    Format an inlineReference response item as markdown.
    Returns a formatted string like `name` or [name](path#Lline).
    """
    name = resp.get('name', '')
    inner_ref = resp.get('inlineReference', {})
    
    if not isinstance(inner_ref, dict):
        return f"`{name}`" if name else ''
    
    # Check if this is a symbol reference (has 'kind' and 'location')
    if 'kind' in inner_ref:
        symbol_name = inner_ref.get('name', name)
        location = inner_ref.get('location', {})
        if location:
            uri = location.get('uri', {})
            path = uri.get('path', '')
            range_info = location.get('range', {})
            line = range_info.get('startLineNumber', '')
            if path and line:
                # Format as [symbol](file#Lline)
                basename = os.path.basename(path)
                return f"`{symbol_name}` ([{basename}:{line}]({path}#L{line}))"
            elif path:
                basename = os.path.basename(path)
                return f"`{symbol_name}` ([{basename}]({path}))"
        return f"`{symbol_name}`" if symbol_name else ''
    
    # File reference - has path in inlineReference
    path = inner_ref.get('path', '')
    if path:
        display_name = name if name else os.path.basename(path)
        return f"[{display_name}]({path})"
    
    # Fallback
    return f"`{name}`" if name else ''


def process_response_stream(responses):
    """
    Process a list of response items.
    Handles the interleaved text and inlineReference pattern.
    Returns a list of (type, content) tuples.
    """
    result_parts = []
    current_text = []
    
    for resp in responses:
        kind = resp.get('kind')
        value = resp.get('value', '')
        
        # Text fragment (no kind, or kind='text')
        if kind is None and 'value' in resp:
            # Plain text fragment, append to current text buffer
            current_text.append(value)
        
        elif kind == 'text':
            current_text.append(value)
        
        elif kind == 'inlineReference':
            # This is an inline reference that should be inserted into text
            ref_text = format_inline_reference(resp)
            current_text.append(ref_text)
        
        elif kind == 'thinking':
            # Flush text buffer first
            if current_text:
                result_parts.append(('text', ''.join(current_text)))
                current_text = []
            if value:
                result_parts.append(('thinking', value))
        
        elif kind == 'prepareToolInvocation':
            # Flush text buffer first
            if current_text:
                result_parts.append(('text', ''.join(current_text)))
                current_text = []
            result_parts.append(('prepareToolInvocation', resp))
        
        elif kind == 'toolInvocationSerialized':
            # Flush text buffer first
            if current_text:
                result_parts.append(('text', ''.join(current_text)))
                current_text = []
            result_parts.append(('toolInvocationSerialized', resp))
        
        elif kind == 'codeblockUri':
            if current_text:
                result_parts.append(('text', ''.join(current_text)))
                current_text = []
            result_parts.append(('codeblockUri', resp))
        
        elif kind == 'textEditGroup':
            if current_text:
                result_parts.append(('text', ''.join(current_text)))
                current_text = []
            result_parts.append(('textEditGroup', resp))
        
        elif kind == 'mcpServersStarting':
            # Ignore this kind
            pass
        
        elif kind == 'undoStop':
            # Ignore
            pass
        
        elif kind == 'progressTaskSerialized':
            # Ignore
            pass
        
        elif kind == 'elicitationSerialized':
            # Ignore
            pass
        
        elif kind == 'confirmation':
            # Ignore
            pass
        
        elif kind == 'agent':
            # Ignore
            pass
        
        else:
            # Unknown kind with value - treat as text
            if value:
                current_text.append(value)
    
    # Flush remaining text
    if current_text:
        result_parts.append(('text', ''.join(current_text)))
    
    return result_parts


def process_chat_json(json_path, output_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return

    # Parse output path to create per-turn filenames
    # e.g., "chat.md" -> "chat_Turn_1.md", "chat_Turn_2.md", ...
    base_path = output_path.rsplit('.', 1)[0]  # Remove extension
    ext = '.md'
    if '.' in os.path.basename(output_path):
        ext = '.' + output_path.rsplit('.', 1)[1]

    # Ensure the output directory exists
    out_dir = os.path.dirname(output_path) if os.path.dirname(output_path) else '.'
    try:
        os.makedirs(out_dir, exist_ok=True)
    except Exception as e:
        print(f"Warning: could not create output directory {out_dir}: {e}")

    requests = data.get('requests', [])
    if not requests:
        print("No requests found in JSON file")
        return

    # Extract session identifier from the first request's ID
    first_request_id = requests[0].get('requestId', '')
    session_file = f"{base_path}.session"
    
    # Check if this is a new session
    old_session_id = None
    if os.path.exists(session_file):
        try:
            with open(session_file, 'r') as f:
                old_session_id = f.read().strip()
        except Exception:
            pass
    
    # If session changed, archive old files
    if old_session_id and old_session_id != first_request_id:
        print(f"New session detected! Archiving old turn files...")
        
        # Create archive folder with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = os.path.join(out_dir, f"archive_{timestamp}")
        
        try:
            os.makedirs(archive_dir, exist_ok=True)
            
            # Move all existing turn files to archive
            import glob
            base_name = os.path.basename(base_path)
            pattern = os.path.join(out_dir, f"{base_name}_Turn_*{ext}")
            old_files = glob.glob(pattern)
            
            for old_file in old_files:
                new_path = os.path.join(archive_dir, os.path.basename(old_file))
                try:
                    os.rename(old_file, new_path)
                    print(f"  Archived: {os.path.basename(old_file)} -> {archive_dir}/")
                except Exception as e:
                    print(f"  Warning: could not archive {old_file}: {e}")
            
            if old_files:
                print(f"Archived {len(old_files)} files to {archive_dir}")
        except Exception as e:
            print(f"Warning: could not create archive directory: {e}")
    
    # Save current session ID
    try:
        with open(session_file, 'w') as f:
            f.write(first_request_id)
    except Exception as e:
        print(f"Warning: could not save session file: {e}")
    
    for i, req in enumerate(requests):
        turn_num = i + 1
        turn_output_path = f"{base_path}_Turn_{turn_num}{ext}"
        
        with open(turn_output_path, 'w', encoding='utf-8') as md_file:
            md_file.write(f"# Turn {turn_num}\n\n")
            
            # User Message
            user_msg = req.get('message', {}).get('text', '')
            md_file.write(f"## User\n\n{user_msg}\n\n")
            
            # Assistant Response
            md_file.write("## Assistant\n\n")
            responses = req.get('response', [])
            
            # Process the response stream
            processed = process_response_stream(responses)
            
            last_tool_name = None
            
            for part_type, content in processed:
                if part_type == 'text':
                    # Write the text content directly
                    text = content.strip()
                    if text:
                        md_file.write(f"{text}\n\n")
                
                elif part_type == 'thinking':
                    md_file.write(f"> **Thinking:** {content}\n\n")
                
                elif part_type == 'prepareToolInvocation':
                    # Store the tool name for the subsequent serialized invocation
                    last_tool_name = content.get('toolName')
                
                elif part_type == 'toolInvocationSerialized':
                    resp = content
                    # Try to get tool name from this object, or fallback to the prepared one
                    tool_name = resp.get('toolName')
                    if not tool_name:
                        tool_name = last_tool_name if last_tool_name else "Unknown Tool"
                    
                    # Clean up tool name if it's "Unknown Tool" but we have info in invocationMessage
                    inv_msg = resp.get('invocationMessage')
                    inv_msg_str = ""
                    if isinstance(inv_msg, dict):
                        inv_msg_str = inv_msg.get('value', '')
                    elif isinstance(inv_msg, str):
                        inv_msg_str = inv_msg
                    
                    # Heuristic: if tool is "Unknown Tool" and message is "Using 'Run in Terminal'", use that.
                    if tool_name == "Unknown Tool" and inv_msg_str.startswith("Using "):
                        tool_name = inv_msg_str.replace("Using ", "").strip('"')

                    # Process Invocation Message for clean file paths
                    if inv_msg_str:
                        path = extract_file_path(inv_msg_str)
                        if "Reading []" in inv_msg_str or "Creating []" in inv_msg_str:
                            action_part = inv_msg_str.split("[]")[0].strip()
                            clean_msg = f"{action_part} {path}"
                        elif "[]" in inv_msg_str and path != inv_msg_str:
                            clean_msg = inv_msg_str.replace(f"[](file://{path})", path)
                            if clean_msg == inv_msg_str:
                                clean_msg = f"{inv_msg_str} ({path})"
                        else:
                            clean_msg = inv_msg_str
                        
                        md_file.write(f"Action: `{clean_msg}`\n\n")

                    # Tool Output
                    tool_data = resp.get('toolSpecificData', {})
                    if tool_data:
                        kind_data = tool_data.get('kind')
                        if kind_data == 'terminal':
                            term_command = tool_data.get('commandLine', {}).get('original', '')
                            if term_command:
                                md_file.write(f"Command:\n```bash\n{term_command}\n```\n")
                            
                            term_output = tool_data.get('terminalCommandOutput', {})
                            text_out = term_output.get('text', '')
                            if text_out:
                                # Clean up terminal output
                                text_out = strip_ansi_codes(text_out)
                                # Truncate long output to keep file size manageable
                                text_out = truncate_output(text_out)
                                md_file.write(f"Output:\n```bash\n{text_out}\n```\n\n")
                        elif kind_data == 'todoList':
                            todos = tool_data.get('todoList', [])
                            md_file.write("**Todo List Updated:**\n")
                            for todo in todos:
                                status = todo.get('status', 'unknown')
                                title = todo.get('title', '')
                                md_file.write(f"- [{status}] {title}\n")
                            md_file.write("\n")
                    
                    # Reset last_tool_name after consumption
                    last_tool_name = None
                
                elif part_type == 'codeblockUri':
                    uri = content.get('uri', {})
                    path = uri.get('path', '')
                    if path:
                        md_file.write(f"**Editing File:** `{path}`\n\n")
                
                elif part_type == 'textEditGroup':
                    edits = content.get('edits', [])
                    if edits:
                        md_file.write("```cpp\n")
                        for edit_group in edits:
                            if isinstance(edit_group, list):
                                for edit in edit_group:
                                    text = edit.get('text', '')
                                    md_file.write(f"{text}\n")
                        md_file.write("```\n\n")

        print(f"  Created: {turn_output_path}")

    print(f"Successfully converted {json_path} to {len(requests)} turn files")


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        process_chat_json(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        input_file = sys.argv[1]
        output_file = input_file.rsplit('.', 1)[0] + '.md'
        process_chat_json(input_file, output_file)
    else:
        process_chat_json('chat.json', 'chat.md')
