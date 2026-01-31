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


# Global variable to store the detected project root
PROJECT_ROOT = None

def detect_project_root(start_path):
    """
    Detect project root by looking for .git folder upwards from start_path.
    If not found, returns None.
    """
    current = os.path.abspath(start_path)
    while True:
        if os.path.exists(os.path.join(current, '.git')):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            # Reached root of filesystem
            return None
        current = parent

def to_relative_path(path):
    """
    Convert absolute path to relative path if within PROJECT_ROOT.
    """
    global PROJECT_ROOT
    if not path or not PROJECT_ROOT:
        return path
        
    # Check if path is within PROJECT_ROOT
    # Normalize paths to ensure consistent comparison
    
    # Handle paths with line numbers (e.g. /path/to/file.cpp#123)
    clean_path = path
    suffix = ""
    if '#' in path:
        clean_path, suffix = path.rsplit('#', 1)
        suffix = '#' + suffix
        
    try:
        abs_path = os.path.abspath(clean_path)
        if abs_path.startswith(PROJECT_ROOT):
            rel = os.path.relpath(abs_path, PROJECT_ROOT)
            return rel + suffix
    except Exception:
        pass
        
    return path


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
                rel_path = to_relative_path(path)
                return f"`{symbol_name}` ([{basename}:{line}]({rel_path}#L{line}))"
            elif path:
                basename = os.path.basename(path)
                rel_path = to_relative_path(path)
                return f"`{symbol_name}` ([{basename}]({rel_path}))"
        return f"`{symbol_name}`" if symbol_name else ''
    
    # File reference - has path in inlineReference
    path = inner_ref.get('path', '')
    if path:
        display_name = name if name else os.path.basename(path)
        rel_path = to_relative_path(path)
        return f"[{display_name}]({rel_path})"
    
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
        if (kind is None and 'value' in resp) or kind == 'text':
            stripped = value.strip()
            # Filter out standalone code block markers or empty strings
            if stripped == '```' or stripped == '':
                pass
            else:
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
                # Pass the whole response object to access generatedTitle if available
                result_parts.append(('thinking', resp))
        
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


def is_continue_message(text):
    """
    Check if the user message indicates a continuation of the previous turn.
    Criteria:
    1. Text is exactly "Continue" (case-insensitive)
    2. Text contains '@agent Continue: "Continue to iterate?"'
    """
    if not text:
        return False
    text = text.strip()
    if text.lower() == 'continue':
        return True
    if '@agent Continue: "Continue to iterate?"' in text:
        return True
    return False


import argparse
import datetime

def process_chat_json(json_path, output_path, no_edit_patch=False, full_terminal=False, html_style=False):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return

    # Create config dict for internal use
    config = {
        'no_edit_patch': no_edit_patch,
        'full_terminal': full_terminal,
        'html_style': html_style
    }

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

    # Detect project root
    global PROJECT_ROOT
    PROJECT_ROOT = detect_project_root(out_dir)
    if PROJECT_ROOT:
        print(f"Project root detected: {PROJECT_ROOT}")
    else:
        print("Could not detect project root (.git not found in parent directories)")

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
        # Create archive folder with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = os.path.join(out_dir, f"archive_{timestamp}")
        
        try:
            os.makedirs(archive_dir, exist_ok=True)
            
            # Move all existing turn files to archive
            import glob
            base_name = os.path.basename(base_path)
            # Match strictly the pattern _turn_X.md or _turn_X-Y.md
            pattern = os.path.join(out_dir, f"{base_name}_turn_*{ext}")
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
    
    # Group requests
    groups = []
    current_group = []
    
    for i, req in enumerate(requests):
        turn_num = i + 1
        user_msg = req.get('message', {}).get('text', '')
        
        if not current_group:
            current_group.append((turn_num, req))
        else:
            if is_continue_message(user_msg):
                current_group.append((turn_num, req))
            else:
                groups.append(current_group)
                current_group = [(turn_num, req)]
    
    if current_group:
        groups.append(current_group)


    def flush_thinking_buffer(buffer, md_file, config):
        if not buffer:
            return
            
        # 1. Determine Main Summary Title (use the last non-empty title, or first if all empty)
        main_title = ""
        for item in reversed(buffer):
            t = item.get('generatedTitle', '')
            if not t:
                # Fallback to first line of value if needed, but per previous logic
                v = item.get('value', '').strip()
                lines = v.split('\n')
                if lines and lines[0].startswith('**') and lines[0].endswith('**'):
                    t = lines[0][2:-2].strip()
            
            if t:
                main_title = t
                break
        
        if not main_title and buffer:
             # Final fallback
             main_title = "Thinking Process"

        # 2. Construct Body
        body_parts = []
        for item in buffer:
            val = item.get('value', '').strip()
            item_title = item.get('generatedTitle', '')
            
            if not val:
                 continue

            lines = val.split('\n')
            first_line = lines[0].strip() if lines else ""
            
            # Determine Section Header
            # Priority: 1. Bold text at start of body (**Title**)
            #           2. generatedTitle
            #           3. Fallback (e.g. "Step")
            
            section_header = ""
            clean_lines = lines
            
            if first_line.startswith('**') and first_line.endswith('**'):
                # Use body's bold header
                section_header = first_line[2:-2].strip()
                clean_lines = lines[1:]
            elif item_title:
                # Use generated title
                section_header = item_title
            
            # Remove title duplicate if it exists in first line of clean_lines (just in case)
            if clean_lines and section_header:
                first = clean_lines[0].strip()
                if first == section_header or first == f"**{section_header}**":
                    clean_lines = clean_lines[1:]
            
            # Remove leading/trailing empty lines to avoid unchecked spacing
            while clean_lines and not clean_lines[0].strip():
                clean_lines.pop(0)
            while clean_lines and not clean_lines[-1].strip():
                clean_lines.pop()
            
            # Construct content for this section
            section_text = ""
            quoted_body = '\n'.join(clean_lines) 
            
            if config['html_style']:
                if section_header:
                    section_text += f"> **{section_header}**\n>\n"
                if quoted_body:
                    # Add > prefix for HTML quote style
                    quoted_body = '\n> '.join(clean_lines)
                    section_text += f"> {quoted_body}"
            else:
                # Flat style
                if section_header:
                    section_text += f"**{section_header}**\n\n"
                if quoted_body:
                    section_text += f"{quoted_body}"

            if section_text:
                body_parts.append(section_text)

        if not body_parts:
             # Empty thinking
             return

        # 3. Render
        if config['html_style']:
            full_body = "\n>\n".join(body_parts)
            md_file.write(f"\n<details>\n<summary>{main_title}</summary>\n\n{full_body}\n\n</details>\n\n")
        else:
            # Codeblock style (Agent/Fullout)
            full_body = "\n\n".join(body_parts)
            md_file.write(f"\n```thinking\n{full_body}\n```\n\n")

    # Process each group
    for group in groups:
        # Determining filename
        # If group has multiple turns, e.g. 6, 7, 8 -> _turn_6-7-8.md
        turn_numbers = [str(t[0]) for t in group]
        turn_range_str = '-'.join(turn_numbers)
        turn_output_path = f"{base_path}_turn_{turn_range_str}{ext}"
        
        with open(turn_output_path, 'w', encoding='utf-8') as md_file:
            first_turn = True
            
            for turn_id, request_obj in group:
                if not first_turn:
                     md_file.write(f"\n{'='*40}\n\n")
                
                md_file.write(f"# Turn {turn_id}\n\n")
                
                # USER Part
                md_file.write("## User\n\n")
                md_file.write(f"{request_obj.get('message', {}).get('text', '')}\n\n")
                
                # ASSISTANT Part
                md_file.write("## Assistant\n\n")
                
                responses = request_obj.get('response', [])
                processed = process_response_stream(responses)
                
                thinking_buffer = []
                last_tool_name = None
                
                for part_type, content in processed:
                    if part_type == 'thinking':
                        thinking_buffer.append(content)
                        continue
                    else:
                        # Flush buffer if we hit a non-thinking part
                        flush_thinking_buffer(thinking_buffer, md_file, config)
                        thinking_buffer = []

                    if part_type == 'text':
                         text = content
                         # Clean up text
                         text = strip_ansi_codes(text)
                         # If text contains only whitespace, skip
                         if text.strip():
                             md_file.write(f"{text}\n\n")
                    
                    elif part_type == 'prepareToolInvocation':
                        # Store the tool name for the subsequent serialized invocation
                        last_tool_name = content.get('toolName')
                    
                    elif part_type == 'toolInvocationSerialized':
                        resp = content
                        
                        # Timestamp (Human Mode)
                        if config['html_style']:
                            ts = None
                            # Try to find timestamp in terminalCommandState
                            tsd = resp.get('toolSpecificData', {})
                            if tsd:
                                # Check terminal state
                                term_state = tsd.get('terminalCommandState', {})
                                if term_state:
                                    ts = term_state.get('timestamp')
                            
                            if ts:
                                # ts is ms
                                dt = datetime.datetime.fromtimestamp(ts/1000.0)
                                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                                md_file.write(f"> **Time:** {time_str}\n\n")

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
                        
                        # Special handling for Apply Patch: Suppress Action output if we are not showing patches 
                        # (because we will show "> **Editing File:** ..." next, keeping it concise)
                        is_apply_patch = "Apply Patch" in tool_name or "Apply Patch" in inv_msg_str
                        if is_apply_patch and config['no_edit_patch']:
                             # Skip outputting the "Action: Using Apply Patch" line
                             pass
                        else:
                            # Process Invocation Message for clean file paths
                            if inv_msg_str:
                                path = extract_file_path(inv_msg_str)
                                # Handle "Reading [](...), lines X to Y" pattern
                                reading_match = re.search(r'(Reading|Creating) \[\]\((.*?)\)(?:, lines (\d+) to (\d+))?', inv_msg_str)
                                if reading_match:
                                    action_verb = reading_match.group(1)
                                    full_uri = reading_match.group(2)
                                    start_line = reading_match.group(3)
                                    end_line = reading_match.group(4)
                                    
                                    clean_path = full_uri
                                    if full_uri.startswith('file://'):
                                        clean_path = full_uri[7:]
                                    
                                    # If we have line range info, update the anchor
                                    if start_line and end_line:
                                        # Remove existing anchor if present
                                        if '#' in clean_path:
                                            clean_path = clean_path.split('#')[0]
                                        clean_path = f"{clean_path}#L{start_line}-L{end_line}"
                                    
                                    res_path = to_relative_path(clean_path)
                                    clean_msg = f"{action_verb} `{res_path}`"
                                
                                elif "[]" in inv_msg_str and path != inv_msg_str:
                                    clean_msg = inv_msg_str.replace(f"[](file://{path})", f"`{to_relative_path(path)}`")
                                    if clean_msg == inv_msg_str:
                                        clean_msg = f"{inv_msg_str} (`{to_relative_path(path)}`)"
                                else:
                                    # For other cases, try to wrap file paths in backticks
                                    # Check if the message contains a file path pattern
                                    if '/' in inv_msg_str and ('.cpp' in inv_msg_str or '.hpp' in inv_msg_str or '.h' in inv_msg_str or '.py' in inv_msg_str):
                                        def replace_path_match(match):
                                            full_path = match.group(0)
                                            if full_path.startswith('**'):
                                                return f"`{full_path}`"
                                            rel = to_relative_path(full_path)
                                            return f"`{rel}`"

                                        clean_msg = re.sub(r'(?<!`)((?:\*\*?|/)[a-zA-Z0-9_\-\./\*\{\}]+)(\.(?:cpp|hpp|h|py|md|txt)(?:#L?\d+-?\d*)?)(?!`)', replace_path_match, inv_msg_str)
                                    else:
                                        clean_msg = inv_msg_str
                                
                                md_file.write(f"> **Action:** {clean_msg}\n\n")

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
                                    text_out = strip_ansi_codes(text_out)
                                    if not full_terminal:
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
                        
                        last_tool_name = None
                    
                    elif part_type == 'codeblockUri':
                        uri = content.get('uri', {})
                        path = uri.get('path', '')
                        if path:
                             last_edit_path = to_relative_path(path)
                        else:
                             last_edit_path = "Unknown File"

                    elif part_type == 'textEditGroup':
                        display_path = locals().get('last_edit_path', 'Code Block')
                        
                        show_patches = not config['no_edit_patch']
                        html_fold = config['html_style']
                        
                        if show_patches:
                            if html_fold:
                                md_file.write(f"\n<details>\n<summary>Editing File: <code>{display_path}</code></summary>\n\n")
                                md_file.write("```cpp\n")
                                edits = content.get('edits', [])
                                if edits:
                                    for edit_group in edits:
                                        if isinstance(edit_group, list):
                                            for edit in edit_group:
                                                text = edit.get('text', '')
                                                md_file.write(f"{text}\n")
                                md_file.write("```\n\n</details>\n\n")
                            else:
                                md_file.write(f"**Editing File:** `{display_path}`\n\n")
                                md_file.write("```cpp\n")
                                edits = content.get('edits', [])
                                if edits:
                                    for edit_group in edits:
                                        if isinstance(edit_group, list):
                                            for edit in edit_group:
                                                text = edit.get('text', '')
                                                md_file.write(f"{text}\n")
                                md_file.write("```\n\n")
                        else:
                            # AGENT/HUMAN (hidden patch) mode
                            # Use Blockquote prefix as requested
                            md_file.write(f"> **Editing File:** `{display_path}`\n\n")
                             
                    # Clear last_edit_path after use to avoid stale data
                    if part_type == 'textEditGroup':
                         last_edit_path = None
                
                # End of turn: flush remaining thinking buffer
                flush_thinking_buffer(thinking_buffer, md_file, config)
                
                md_file.write("---\n\n")
                first_turn = False



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert GitHub Copilot JSON logs to Markdown.')
    parser.add_argument('input', nargs='?', default='chat.json', help='Input JSON file path (default: chat.json)')
    parser.add_argument('output', nargs='?', help='Output Markdown file path (default: Same basename as input + .md)')
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('-agent', action='store_true', help='Agent mode (Default): Flat format, no HTML, code block thinking, hidden edits.')
    mode_group.add_argument('-human', action='store_true', help='Human mode: VS Code style, HTML folding, hidden edits (folded view).')
    mode_group.add_argument('-fullout', action='store_true', help='Fullout mode: Agent style but with visible edits.')
    
    # Legacy args (kept for compatibility or mapped)
    parser.add_argument('--noeditpatch', action='store_true', help='Legacy: Hide edit patches.')
    parser.add_argument('--fullterminal', action='store_true', help='Do not truncate terminal output.')
    parser.add_argument('--fold', action='store_true', help='Legacy: Enable fold (HTML style).')

    args = parser.parse_args()
    
    input_file = args.input
    output_file = args.output
    
    if output_file is None:
        if input_file == 'chat.json':
            output_file = 'chat.md'
        else:
            output_file = input_file.rsplit('.', 1)[0] + '.md'

    # Determine configuration based on mode
    # Default is Agent mode
    config = {
        'no_edit_patch': True,
        'html_style': False,
        'full_terminal': args.fullterminal
    }

    if args.human:
        config['no_edit_patch'] = True
        config['html_style'] = True
    elif args.fullout:
        config['no_edit_patch'] = False
        config['html_style'] = False
    elif args.agent:
        # Default
        pass
    else:
        # If no mode specified, check legacy flags or default to Agent
        if args.fold:
            config['html_style'] = True
        if args.noeditpatch: 
             config['no_edit_patch'] = True
        # If neither logic above applies, we fall back to Agent default (no_edit=True, html=False)

    process_chat_json(input_file, output_file, **config)
