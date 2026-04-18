#!/usr/bin/env python3
"""
acat - AI CLI Agent Tool using Ollama
Core engine with tool calling, file operations, and project scaffolding
"""

import os
import sys
import json
import subprocess
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False
import re
import shutil
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Enable ANSI escape codes on Windows
_ANSI_SUPPORTED = True
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    _ANSI_SUPPORTED = False
    for handle_id in (-11, -12):  # STD_OUTPUT_HANDLE, STD_ERROR_HANDLE
        handle = kernel32.GetStdHandle(handle_id)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            if kernel32.SetConsoleMode(handle, mode.value | 0x0004):
                _ANSI_SUPPORTED = True

# Strip ANSI escape codes on terminals that don't support them
_ANSI_RE = re.compile(r'\033\[[0-9;]*m')

def _strip_ansi(text):
    """Remove ANSI escape codes if terminal doesn't support them."""
    if _ANSI_SUPPORTED:
        return text
    return _ANSI_RE.sub('', text)

# Replace built-in print with ANSI-aware version
_original_print = print

def print(*args, **kwargs):
    """Print that strips ANSI codes on terminals that don't support them."""
    text = ' '.join(str(a) for a in args)
    text = _strip_ansi(text)
    _original_print(text, **kwargs)

# prompt_toolkit for better completion (optional)
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.styles import Style
    from prompt_toolkit.key_binding import KeyBindings
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

# Global flag for hint display
_show_hint = False

# Default configuration
DEFAULT_MODEL = "gemma4:latest"
DEFAULT_PROVIDER = "ollama"
DEFAULT_API_ENDPOINT = "https://api.openai.com/v1"
DEFAULT_GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_GROQ_ENDPOINT = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
ACAT_CONFIG_DIR = Path.home() / ".acat"
ACAT_CONFIG_FILE = ACAT_CONFIG_DIR / "config.json"
ACAT_MD_FILE = "ACAT.md"

# Tool definitions for Ollama
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. ALWAYS provide 'path' (including folder, e.g. 'utils/ExcelUtils.cs') and 'content'. Create the directory first with create_directory if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Full file path including folder, e.g. 'utils/ExcelUtils.cs'. NEVER leave this empty."},
                    "content": {"type": "string", "description": "Complete file content to write"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path"},
                    "recursive": {"type": "boolean", "description": "Search recursively"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files matching a glob pattern (use '**/*.cs' for recursive search)",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern to match"},
                    "path": {"type": "string", "description": "Base directory to search"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "cwd": {"type": "string", "description": "Working directory"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Create a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to create"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_exists",
            "description": "Check if a file or directory exists",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to check"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to delete"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scaffold_project",
            "description": "Create a new project from template",
            "parameters": {
                "type": "object",
                "properties": {
                    "template": {"type": "string", "description": "Template name (static-web, spring-boot, wpf-csharp, react, react-native, electron)"},
                    "name": {"type": "string", "description": "Project name"},
                    "path": {"type": "string", "description": "Destination path"}
                },
                "required": ["template", "name"]
            }
        }
    }
]

# Spinner animation characters
SPINNER_CHARS = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']


class AcatAgent:
    """Main agent class for acat CLI"""

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.config = self._load_config()
        self.provider = self.config.get("provider", DEFAULT_PROVIDER)
        # Load provider-specific keys and endpoints
        self._load_provider_credentials()
        self.conversation_history: List[Dict] = []
        self.conversation_history: List[Dict] = []
        self.working_dir = Path.cwd()
        self.stop_flag = False
        self.cancel_current = False  # Flag to cancel current operation (Esc key)
        self._file_list_cache: List[str] = None
        self._file_list_timestamp: float = 0
        self._refresh_file_list()
        self.show_explanation = True  # Toggle for showing/hiding explanations
        self._loading_done = True  # Flag to control loading animation
        self._files_written = set()  # Track files written in current request
        self._created_dirs = []  # Track directories created in current request

    def _start_loading(self):
        """Start loading animation thread"""
        self._loading_done = False
        self._loading_start_time = time.time()
        self._loading_thread = threading.Thread(target=self._loading_animation, daemon=True)
        self._loading_thread.start()

    def _stop_loading(self):
        """Stop loading animation and clear the line"""
        self._loading_done = True
        if hasattr(self, '_loading_thread') and self._loading_thread.is_alive():
            self._loading_thread.join(timeout=1)
        sys.stdout.write(_strip_ansi('\r\033[K'))
        sys.stdout.flush()

    def _loading_animation(self):
        """Show spinner and timer animation while processing"""
        idx = 0
        while not self._loading_done:
            elapsed = int(time.time() - self._loading_start_time)
            timer = str(timedelta(seconds=elapsed)).zfill(8)[:8]
            spinner = SPINNER_CHARS[idx % len(SPINNER_CHARS)]
            sys.stdout.write(_strip_ansi(f'\r\033[K\033[38;5;208m  {spinner} Thinking... {timer}\033[0m'))
            sys.stdout.flush()
            idx += 1
            time.sleep(0.15)

    def _load_config(self) -> Dict:
        """Load configuration from file"""
        if ACAT_CONFIG_FILE.exists():
            try:
                with open(ACAT_CONFIG_FILE, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    return data if data else {"model": DEFAULT_MODEL}
            except (json.JSONDecodeError, ValueError):
                # Config file is empty or corrupt — start fresh
                pass
        return {"model": DEFAULT_MODEL}

    def _save_config(self):
        """Save configuration to file"""
        ACAT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(ACAT_CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _load_provider_credentials(self):
        """Load API key and endpoint for the current provider from config"""
        # Per-provider keys: openai_key, gemini_key, groq_key
        # Per-provider endpoints: openai_endpoint, gemini_endpoint, groq_endpoint
        # Migrate legacy single key/endpoint to per-provider format
        legacy_key = self.config.get("api_key", "")
        if legacy_key and not self.config.get(f"{self.provider}_key"):
            self.config[f"{self.provider}_key"] = legacy_key

        self.api_key = self.config.get(f"{self.provider}_key", "")

        # Default endpoints per provider
        default_endpoints = {
            "openai": DEFAULT_API_ENDPOINT,
            "gemini": DEFAULT_GEMINI_ENDPOINT,
            "groq": DEFAULT_GROQ_ENDPOINT,
        }
        # Migrate legacy single endpoint
        legacy_endpoint = self.config.get("api_endpoint", "")
        if legacy_endpoint and not self.config.get(f"{self.provider}_endpoint"):
            # Only migrate if it matches the provider's default pattern
            self.config[f"{self.provider}_endpoint"] = legacy_endpoint

        self.api_endpoint = self.config.get(f"{self.provider}_endpoint",
                                            default_endpoints.get(self.provider, DEFAULT_API_ENDPOINT))

    def _save_provider_credentials(self):
        """Save API key and endpoint for the current provider to config"""
        if self.api_key:
            self.config[f"{self.provider}_key"] = self.api_key
        self.config[f"{self.provider}_endpoint"] = self.api_endpoint
        self._save_config()

    def _refresh_file_list(self):
        """Refresh the background file list cache"""
        import time
        try:
            files = []
            for root, dirs, filenames in os.walk(self.working_dir):
                # Skip hidden directories and common ignore patterns
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'node_modules', 'venv', '.git')]
                for f in filenames:
                    if not f.startswith('.'):
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, self.working_dir)
                        files.append(rel_path)
            self._file_list_cache = sorted(files)
            self._file_list_timestamp = time.time()
        except Exception as e:
            self._file_list_cache = []

    def _get_file_list(self) -> List[str]:
        """Get the cached file list, always refreshing to ensure latest state"""
        # Always refresh to ensure we have the latest file state
        self._refresh_file_list()
        return self._file_list_cache

    def _get_file_tree_context(self) -> str:
        """Get a formatted file tree context for the AI"""
        files = self._get_file_list()
        if not files:
            return "(empty directory)"

        # Build a tree structure
        lines = []
        prev_parts = []

        for file_path in files[:500]:  # Limit to 500 files for context
            parts = file_path.split(os.sep)
            indent = 0
            for i, part in enumerate(parts[:-1]):
                if i >= len(prev_parts) or prev_parts[i] != part:
                    lines.append("  " * i + f"{part}/")
            prev_parts = parts[:-1]
            lines.append("  " * (len(parts) - 1) + parts[-1])

        if len(files) > 500:
            lines.append(f"... and {len(files) - 500} more files")

        return "\n".join(lines)

    def _read_all_files_contents(self) -> Dict[str, str]:
        """Read contents of ALL files recursively for complete project analysis"""
        files_content = {}
        files = self._get_file_list()

        # File extensions to prioritize (code files)
        code_extensions = {'.py', '.cs', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs',
                          '.xaml', '.xml', '.json', '.yaml', '.yml', '.html', '.css', '.md',
                          '.sh', '.ps1', '.config', '.sql', '.graphql', '.proto'}

        for file_path in files:
            full_path = self.working_dir / file_path

            # Skip binary files and large files
            try:
                # Check file size (skip files > 100KB)
                if full_path.stat().st_size > 100 * 1024:
                    continue

                # Read file content
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Store with relative path as key
                files_content[file_path] = content

            except Exception as e:
                # Skip files that can't be read
                continue

        return files_content

    def _get_full_project_context(self) -> str:
        """Get complete project context including file tree AND all file contents"""
        files = self._get_file_list()

        if not files:
            return "(empty directory)"

        # Build file tree
        tree_lines = []
        prev_parts = []

        for file_path in files[:500]:
            parts = file_path.split(os.sep)
            for i, part in enumerate(parts[:-1]):
                if i >= len(prev_parts) or prev_parts[i] != part:
                    tree_lines.append("  " * i + f"{part}/")
            prev_parts = parts[:-1]
            tree_lines.append("  " * (len(parts) - 1) + parts[-1])

        if len(files) > 500:
            tree_lines.append(f"... and {len(files) - 500} more files")

        file_tree = "\n".join(tree_lines)

        # Read all file contents
        files_content = self._read_all_files_contents()

        # Build complete context
        context_parts = [f"[File Tree - {len(files)} files total]", file_tree, ""]
        context_parts.append(f"[File Contents - {len(files_content)} files read]")
        context_parts.append("=" * 50)

        for file_path, content in files_content.items():
            # Truncate very long files but keep them readable
            if len(content) > 5000:
                content = content[:2500] + "\n... [truncated] ...\n" + content[-2500:]

            context_parts.append(f"\n--- {file_path} ---")
            context_parts.append(content)
            context_parts.append("")

        return "\n".join(context_parts)

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Execute a tool and return result"""
        # Auto-correct common tool name mistakes
        if tool_name == "search_file":
            tool_name = "search_files"
        elif tool_name == "search_code":
            tool_name = "search_files"
        elif tool_name == "execute_bash":
            tool_name = "run_command"
        try:
            if tool_name == "read_file":
                path = self._resolve_path(args.get("path", ""))
                if not path.exists():
                    return f"Error: File not found: {path}"
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()

            elif tool_name == "write_file":
                path = self._resolve_path(args.get("path", ""))
                content = args.get("content", "")
                # Validate: empty path is invalid
                if not args.get("path", "").strip():
                    hint = "Provide the file path including directory."
                    if self._created_dirs:
                        dirs = ", ".join(self._created_dirs)
                        hint += f" Available directories: {dirs}. Example: '{self._created_dirs[0]}/filename.cs'"
                    return f"Error: write_file requires a 'path' argument. {hint}"
                # Validate: path must not be a directory
                if path.exists() and path.is_dir():
                    return f"Error: '{path}' is a directory, not a file. Specify the full file path, e.g. '{args.get('path', '')}/SomeFile.cs'."
                # Fix directory casing to match existing filesystem
                file_arg = args.get("path", "").strip()
                fixed_path = self._fix_path_casing(file_arg)
                if fixed_path != file_arg:
                    args["path"] = fixed_path
                    path = self._resolve_path(fixed_path)
                # Smart path: if file has no directory and we recently created one, try to match
                file_arg = args.get("path", "").strip()
                if not os.path.dirname(file_arg) and self._created_dirs:
                    # Bare filename with no directory — check if a created dir matches
                    filename = Path(file_arg).stem
                    for created_dir in self._created_dirs:
                        dir_name = Path(created_dir).name
                        # Match if the class name relates to the directory name
                        if filename.lower().startswith(dir_name.lower()) or dir_name.lower() in filename.lower():
                            path = self._resolve_path(os.path.join(created_dir, file_arg))
                            break
                path.parent.mkdir(parents=True, exist_ok=True)
                # Replace placeholder namespaces with actual project namespace
                content = self._replace_placeholder_namespaces(content)
                # Fix namespace/using casing in content to match actual directory casing
                # e.g. if content has "namespace SkyKSolution.Utils" but folder is "utils"
                import re
                path_parts = list(path.relative_to(self.working_dir).parent.parts)
                fixed_content = content
                for dir_part in path_parts:
                    # Only fix casing in namespace and using lines
                    lines = fixed_content.split('\n')
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if stripped.startswith('namespace ') or stripped.startswith('using '):
                            # Replace case-insensitive occurrences of this dir name
                            pattern = re.compile(r'(?<!\w)' + re.escape(dir_part) + r'(?!\w)', re.IGNORECASE)
                            lines[i] = pattern.sub(dir_part, line)
                    fixed_content = '\n'.join(lines)
                content = fixed_content
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                # Refresh file list after writing
                self._refresh_file_list()
                # Auto-commit if in git repository
                self._auto_git_commit(str(path))
                return f"Successfully wrote to {path}"

            elif tool_name == "list_files":
                path = self._resolve_path(args.get("path", "."))
                recursive = args.get("recursive", False)
                if not path.exists():
                    return f"Error: Directory not found: {path}"
                if recursive:
                    files = []
                    for root, dirs, filenames in os.walk(path):
                        for f in filenames:
                            files.append(os.path.join(root, f))
                    return "\n".join(files)
                else:
                    return "\n".join(str(p) for p in path.iterdir())

            elif tool_name == "search_files":
                pattern = args.get("pattern", "*")
                base_path = self._resolve_path(args.get("path", "."))
                if not base_path.exists():
                    return f"Error: Directory not found: {base_path}"
                matches = list(base_path.glob(pattern))
                return "\n".join(str(m) for m in matches)

            elif tool_name == "run_command":
                cmd = args.get("command", "")
                cwd = args.get("cwd", str(self.working_dir))
                result = subprocess.run(
                    cmd, shell=True, capture_output=True,
                    text=True, cwd=cwd, timeout=60
                )
                output = result.stdout
                if result.stderr:
                    output += "\n" + result.stderr
                return output or "(no output)"

            elif tool_name == "create_directory":
                path = self._resolve_path(args.get("path", ""))
                if path.exists() and path.is_dir():
                    rel_path = os.path.relpath(str(path), str(self.working_dir))
                    return f"Directory already exists: {path}. You can write files to it using path '{rel_path}/filename'."
                path.mkdir(parents=True, exist_ok=True)
                # Track created directory for smart path resolution
                rel_path = os.path.relpath(str(path), str(self.working_dir))
                self._created_dirs.append(rel_path)
                # Refresh file list after creating directory
                self._refresh_file_list()
                # Auto-commit if in git repository
                self._auto_git_commit(str(path))
                return f"Created directory: {path}. Write files to it using path like '{rel_path}/filename.cs'."

            elif tool_name == "file_exists":
                path = self._resolve_path(args.get("path", ""))
                return "true" if path.exists() else "false"

            elif tool_name == "delete_file":
                path = self._resolve_path(args.get("path", ""))
                if not path.exists():
                    return f"Error: File not found: {path}"
                if path.is_dir():
                    return f"Error: Cannot delete directory (use rm -r manually): {path}"
                path.unlink()
                # Refresh file list after deleting
                self._refresh_file_list()
                # Auto-commit if in git repository
                self._auto_git_commit(str(path))
                return f"Successfully deleted {path}"

            elif tool_name == "scaffold_project":
                template = args.get("template", "")
                name = args.get("name", "")
                dest = self._resolve_path(args.get("path", name))
                result = self._scaffold(template, name, dest)
                # Auto-commit scaffolded project
                self._auto_git_commit(str(dest))
                return result

            else:
                return f"Error: Unknown tool: {tool_name}"

        except subprocess.TimeoutExpired:
            return "Error: Command timed out (60s limit)"
        except Exception as e:
            return f"Error: {str(e)}"

    def _is_git_repo(self) -> bool:
        """Check if current directory is a git repository"""
        git_dir = self.working_dir / ".git"
        return git_dir.exists() and git_dir.is_dir()

    def _auto_git_commit(self, file_path: str):
        """Automatically stage and commit file changes if in a git repository"""
        if not self._is_git_repo():
            return

        try:
            # Stage the specific file
            subprocess.run(
                ["git", "add", file_path],
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=10
            )

            # Check if there are staged changes to commit
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.stdout.strip():
                # Create commit message
                commit_msg = f"AI: Update {os.path.basename(file_path)}"

                commit_result = subprocess.run(
                    ["git", "commit", "-m", commit_msg, "--no-verify"],
                    cwd=self.working_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if commit_result.returncode == 0:
                    print(f"  [Git] Committed: {commit_msg}")
                else:
                    print(f"  [Git] Commit failed: {commit_result.stderr}")
            else:
                print(f"  [Git] File already staged or no changes")

        except subprocess.TimeoutExpired:
            print("  [Git] Operation timed out")
        except Exception as e:
            print(f"  [Git] Error: {str(e)}")

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to working directory"""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.working_dir / p

    def _fix_path_casing(self, file_path: str) -> str:
        """Fix directory casing in a path to match existing filesystem or _created_dirs.
        E.g., 'Utils/ExcelUtils.cs' -> 'utils/ExcelUtils.cs' if 'utils' exists on disk."""
        parts = file_path.replace("\\", "/").split("/")
        fixed_parts = []
        for i, part in enumerate(parts):
            is_last = (i == len(parts) - 1)
            if is_last:
                fixed_parts.append(part)
                continue
            # This is a directory component - check for casing mismatch
            found = False
            # Check against _created_dirs
            for created_dir in self._created_dirs:
                created_parts = created_dir.replace("\\", "/").split("/")
                if i < len(created_parts) and created_parts[i].lower() == part.lower():
                    fixed_parts.append(created_parts[i])
                    found = True
                    break
            if found:
                continue
            # Check against actual filesystem
            parent_path = self._resolve_path("/".join(fixed_parts)) if fixed_parts else self.working_dir
            if parent_path.exists() and parent_path.is_dir():
                for existing in parent_path.iterdir():
                    if existing.is_dir() and existing.name.lower() == part.lower():
                        fixed_parts.append(existing.name)
                        found = True
                        break
            if not found:
                fixed_parts.append(part)
        return "/".join(fixed_parts)

    def _replace_placeholder_namespaces(self, content: str) -> str:
        """Replace placeholder namespaces like YourAppName, YourNamespace with the actual project namespace."""
        placeholders = ['YourAppName', 'YourNamespace', 'YourProjectNamespace',
                        'MyApp', 'MyNamespace', 'AppName', 'ProjectName']
        # Skip if no placeholders found
        if not any(p in content for p in placeholders):
            return content
        # Detect actual project namespace from existing files
        actual_namespace = None
        try:
            for existing_file in Path(self.working_dir).rglob("*.cs"):
                with open(existing_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        ns_match = re.match(r'namespace\s+([\w.]+)', line.strip())
                        if ns_match:
                            actual_namespace = ns_match.group(1)
                            break
                if actual_namespace:
                    break
            if not actual_namespace:
                for existing_file in Path(self.working_dir).rglob("*.xaml"):
                    with open(existing_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            cls_match = re.match(r'x:Class="([\w.]+)"', line.strip())
                            if cls_match:
                                actual_namespace = cls_match.group(1).rsplit('.', 1)[0]
                                break
                    if actual_namespace:
                        break
        except Exception:
            pass
        if actual_namespace:
            for placeholder in placeholders:
                if placeholder in content:
                    content = content.replace(placeholder, actual_namespace)
        return content

    def _infer_file_path(self, content: str) -> str:
        """Infer a file path from code content when the model omits it.
        Extracts class name, namespace, and language to construct a path."""
        if not content:
            return ""

        # Detect language and extract class/namespace
        class_name = None
        namespace = None
        ext = None

        # C# detection
        cs_class = re.search(r'(?:public|internal|private)\s+(?:static\s+)?(?:class|struct|interface)\s+(\w+)', content)
        cs_ns = re.search(r'namespace\s+([\w.]+)', content)
        if cs_class:
            class_name = cs_class.group(1)
            ext = '.cs'
            if cs_ns:
                # Take the last segment of the namespace as the folder
                namespace = cs_ns.group(1).split('.')[-1]

        # Python detection
        if not class_name:
            py_class = re.search(r'^class\s+(\w+)', content, re.MULTILINE)
            if py_class:
                class_name = py_class.group(1)
                ext = '.py'

        # Java detection
        if not class_name:
            java_class = re.search(r'(?:public|private|protected)\s+(?:class|interface)\s+(\w+)', content)
            java_ns = re.search(r'package\s+([\w.]+)', content)
            if java_class:
                class_name = java_class.group(1)
                ext = '.java'
                if java_ns:
                    namespace = java_ns.group(1).replace('.', '/')

        # JavaScript/TypeScript detection
        if not class_name:
            js_class = re.search(r'(?:export\s+)?(?:default\s+)?(?:class|function)\s+(\w+)', content)
            if js_class:
                class_name = js_class.group(1)
                ext = '.js' if 'typescript' not in content.lower() and ': ' not in content[:200] else '.ts'

        # XAML detection
        if not class_name and '<Window' in content or '<Page' in content or '<UserControl' in content:
            xaml_class = re.search(r'x:Class="[\w.]+\.(\w+)"', content)
            if xaml_class:
                class_name = xaml_class.group(1)
                ext = '.xaml'

        if not class_name:
            return ""

        filename = f"{class_name}{ext}"

        # Created directories always take priority — the user explicitly asked for them
        if self._created_dirs:
            # Try exact match first (class name relates to dir name)
            for created_dir in self._created_dirs:
                dir_name = Path(created_dir).name
                if class_name.lower().startswith(dir_name.lower()) or dir_name.lower() in class_name.lower():
                    return os.path.join(created_dir, filename)

            # No exact match — use the first created directory as default
            # The user likely wants the file in the directory they just created
            return os.path.join(self._created_dirs[0], filename)

        # Use namespace as directory only if it's not a placeholder
        placeholder_names = ['yournamespace', 'namespace1', 'mynamespace', 'templatename', 'defaultnamespace']
        if namespace and ext == '.cs' and namespace.lower() not in placeholder_names:
            return os.path.join(namespace, filename)

        return filename

    def _scaffold(self, template: str, name: str, dest: Path) -> str:
        """Scaffold a new project from template"""
        templates_dir = Path(__file__).parent.parent / "templates"

        # Normalize template name: lowercase, strip whitespace
        template = template.strip().lower()

        # Replace underscores with hyphens for consistency
        template = template.replace("_", "-")

        template_path = templates_dir / template

        # If exact match fails, try fuzzy matching
        if not template_path.exists():
            available = [d.name for d in templates_dir.iterdir() if d.is_dir()]

            # Try to find a case-insensitive match
            for avail in available:
                if avail.lower() == template:
                    template = avail
                    template_path = templates_dir / template
                    break

            # Still not found - return helpful error
            if not template_path.exists():
                return f"Error: Template not found: {template}\nAvailable templates: {', '.join(sorted(available))}"

        if dest.exists():
            return f"Error: Destination already exists: {dest}"

        shutil.copytree(template_path, dest)

        # Replace placeholder name in files and rename files/directories
        for root, dirs, files in os.walk(dest):
            # Rename directories with placeholder
            for d in dirs:
                if "{{PROJECT_NAME}}" in d:
                    old_dir = Path(root) / d
                    new_dir = Path(root) / d.replace("{{PROJECT_NAME}}", name)
                    old_dir.rename(new_dir)

            # Process files
            for f in files:
                filepath = Path(root) / f

                # Rename file if it contains placeholder
                if "{{PROJECT_NAME}}" in f:
                    new_filename = f.replace("{{PROJECT_NAME}}", name)
                    new_filepath = Path(root) / new_filename
                    filepath.rename(new_filepath)
                    filepath = new_filepath

                # Replace placeholder in file content
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        content = file.read()
                    content = content.replace("{{PROJECT_NAME}}", name)
                    content = content.replace("{{project-name}}", name.lower().replace(" ", "-"))
                    with open(filepath, 'w', encoding='utf-8') as file:
                        file.write(content)
                except:
                    pass  # Skip binary files

        return f"Created project '{name}' at {dest}"

    def _call_api(self, messages: List[Dict], tools: List[Dict] = None) -> Dict:
        """Call the appropriate AI API based on current provider"""
        if self.provider == "openai" or self.provider == "groq":
            return self._call_openai(messages, tools)
        elif self.provider == "gemini":
            return self._call_gemini(messages, tools)
        else:
            return self._call_ollama(messages, tools)

    def _call_ollama(self, messages: List[Dict], tools: List[Dict] = None) -> Dict:
        """Call Ollama API with messages and optional tools"""
        import urllib.request
        import urllib.error

        url = "http://localhost:11434/api/chat"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }

        if tools:
            payload["tools"] = tools

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, data=data,
            headers={'Content-Type': 'application/json'}
        )

        # Start loading animation during API call
        self._start_loading()

        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.URLError as e:
            return {"error": f"Ollama connection error: {e.reason}. Is Ollama running? Start with: ollama serve"}
        except Exception as e:
            return {"error": f"Ollama error: {str(e)}"}
        finally:
            # Stop loading animation and clear the line
            self._stop_loading()

    def _call_openai(self, messages: List[Dict], tools: List[Dict] = None) -> Dict:
        """Call OpenAI-compatible API with messages and optional tools"""
        import urllib.request
        import urllib.error

        if not self.api_key:
            return {"error": "No API key set. Use /key <your-api-key> to set it, or /provider ollama to switch back to offline mode."}

        url = f"{self.api_endpoint.rstrip('/')}/chat/completions"

        # Normalize messages for OpenAI format: tool_calls arguments must be JSON strings
        normalized_messages = []
        for msg in messages:
            m = dict(msg)
            if m.get("role") == "assistant" and m.get("tool_calls"):
                new_tool_calls = []
                for tc in m["tool_calls"]:
                    tc2 = dict(tc)
                    func = dict(tc2.get("function", {}))
                    # OpenAI requires arguments as a JSON string
                    if "arguments" in func and not isinstance(func["arguments"], str):
                        func["arguments"] = json.dumps(func["arguments"])
                    tc2["function"] = func
                    # Add required id and type fields if missing
                    if "id" not in tc2:
                        tc2["id"] = f"call_{hash(str(func)) & 0xFFFFFFFF:x}"
                    if "type" not in tc2:
                        tc2["type"] = "function"
                    new_tool_calls.append(tc2)
                m["tool_calls"] = new_tool_calls
            normalized_messages.append(m)

        payload = {
            "model": self.model,
            "messages": normalized_messages,
            "stream": False
        }

        if tools:
            payload["tools"] = tools

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, data=data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
                'User-Agent': 'acat-cli/1.0'
            }
        )

        # Start loading animation during API call
        self._start_loading()

        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                raw = json.loads(response.read().decode('utf-8'))
                # Normalize OpenAI response to Ollama format
                return self._normalize_openai_response(raw)
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode('utf-8')
            except:
                pass
            # Try to extract detailed error message from JSON body
            detail = ""
            try:
                err_json = json.loads(error_body)
                err_obj = err_json.get("error", {})
                if isinstance(err_obj, dict):
                    detail = err_obj.get("message", "")
                elif isinstance(err_obj, str):
                    detail = err_obj
            except (json.JSONDecodeError, AttributeError):
                detail = error_body[:200]

            if e.code == 401:
                return {"error": f"API key is invalid or missing. Use /key <your-api-key> to set a valid key, or /provider ollama to switch to offline mode."}
            elif e.code == 429:
                return {"error": f"Rate limit or quota exceeded: {detail}. Check your API key and billing at your provider dashboard."}
            elif e.code == 404:
                return {"error": f"Model '{self.model}' not found at {self.api_endpoint}. Use /model to set a valid model name."}
            elif e.code == 400:
                # Retry without tools if tool calling fails (common with Groq)
                if tools and ("function" in detail.lower() or "tool" in detail.lower()):
                    payload_no_tools = {
                        "model": self.model,
                        "messages": messages,
                        "stream": False
                    }
                    data2 = json.dumps(payload_no_tools).encode('utf-8')
                    req2 = urllib.request.Request(
                        url, data=data2,
                        headers={
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {self.api_key}',
                            'User-Agent': 'acat-cli/1.0'
                        }
                    )
                    try:
                        with urllib.request.urlopen(req2, timeout=120) as response2:
                            raw2 = json.loads(response2.read().decode('utf-8'))
                            return self._normalize_openai_response(raw2)
                    except Exception:
                        pass
                return {"error": f"API error 400: {detail[:300]}"}
            return {"error": f"API error {e.code}: {detail[:300]}"}
        except urllib.error.URLError as e:
            return {"error": f"Connection error: {e.reason}. Check your /endpoint setting."}
        except Exception as e:
            return {"error": f"API error: {str(e)}"}
        finally:
            # Stop loading animation and clear the line
            self._stop_loading()

    def _normalize_openai_response(self, raw: Dict) -> Dict:
        """Normalize OpenAI API response to Ollama format"""
        try:
            # Check for Groq failed_generation
            choice = raw.get("choices", [{}])[0]
            finish_reason = choice.get("finish_reason", "")
            if finish_reason == "tool_calls_failed" or "failed_generation" in choice:
                failed = choice.get("failed_generation", "Tool call failed")
                return {"error": f"Tool call failed: {failed}"}

            msg = choice.get("message", {})
            content = msg.get("content", "") or ""
            tool_calls = msg.get("tool_calls", [])

            # Convert OpenAI tool calls to Ollama format
            normalized_calls = []
            for tc in tool_calls:
                func = tc.get("function", {})
                arguments = func.get("arguments", "{}")
                # OpenAI sends arguments as a JSON string, parse it
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                normalized_calls.append({
                    "function": {
                        "name": func.get("name", ""),
                        "arguments": arguments
                    }
                })

            return {
                "message": {
                    "content": content,
                    "tool_calls": normalized_calls if normalized_calls else None
                }
            }
        except (IndexError, KeyError, TypeError) as e:
            return {"error": f"Failed to parse API response: {str(e)}"}

    def _convert_tools_to_gemini(self, tools: List[Dict]) -> List[Dict]:
        """Convert OpenAI-format tools to Gemini functionDeclarations format"""
        function_declarations = []
        for tool in tools:
            func = tool.get("function", {})
            func_decl = {
                "name": func.get("name", ""),
                "description": func.get("description", ""),
            }
            parameters = func.get("parameters", {})
            if parameters:
                func_decl["parameters"] = parameters
            function_declarations.append(func_decl)
        # Gemini wraps all declarations in a single "tools" entry
        return [{"functionDeclarations": function_declarations}]

    def _call_gemini(self, messages: List[Dict], tools: List[Dict] = None) -> Dict:
        """Call Google Gemini API with messages and optional tools"""
        import urllib.request
        import urllib.error

        if not self.api_key:
            return {"error": "No API key set. Use /key <your-gemini-api-key> to set it, or /provider ollama to switch to offline mode."}

        # Extract system instruction from messages (Gemini uses separate field)
        system_instruction = None
        contents = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                system_instruction = content
                continue

            if role == "user":
                parts = [{"text": content}]
                contents.append({"role": "user", "parts": parts})

            elif role == "assistant":
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    parts = []
                    if content:
                        parts.append({"text": content})
                    for tc in tool_calls:
                        func = tc.get("function", {})
                        name = func.get("name", "")
                        arguments = func.get("arguments", {})
                        if isinstance(arguments, str):
                            try:
                                arguments = json.loads(arguments)
                            except json.JSONDecodeError:
                                arguments = {}
                        parts.append({
                            "functionCall": {
                                "name": name,
                                "args": arguments
                            }
                        })
                    contents.append({"role": "model", "parts": parts})
                else:
                    parts = []
                    if content:
                        parts.append({"text": content})
                    if parts:
                        contents.append({"role": "model", "parts": parts})

            elif role == "tool":
                # Tool result - becomes functionResponse in user role
                tool_name = msg.get("name", msg.get("tool_call_id", ""))
                result_text = content if content else ""
                contents.append({
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": tool_name,
                            "response": {"result": result_text}
                        }
                    }]
                })

        # Build request payload
        payload = {"contents": contents}

        if system_instruction:
            payload["system_instruction"] = {
                "parts": [{"text": system_instruction}]
            }

        if tools:
            payload["tools"] = self._convert_tools_to_gemini(tools)

        # Build URL with API key as query parameter
        model_name = self.model
        url = f"{self.api_endpoint.rstrip('/')}/models/{model_name}:generateContent?key={self.api_key}"

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, data=data,
            headers={'Content-Type': 'application/json'}
        )

        self._start_loading()

        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                raw = json.loads(response.read().decode('utf-8'))
                return self._normalize_gemini_response(raw)
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode('utf-8')
            except:
                pass
            detail = ""
            try:
                err_json = json.loads(error_body)
                err_obj = err_json.get("error", {})
                if isinstance(err_obj, dict):
                    detail = err_obj.get("message", "")
                elif isinstance(err_obj, str):
                    detail = err_obj
            except (json.JSONDecodeError, AttributeError):
                detail = error_body[:200]

            if e.code == 400:
                return {"error": f"Gemini API bad request: {detail[:300]}. Check your model name and request format."}
            elif e.code in (401, 403):
                return {"error": f"Gemini API key is invalid or missing. Use /key <your-api-key> to set a valid key, or get one at https://aistudio.google.com/apikey"}
            elif e.code == 429:
                return {"error": f"Gemini rate limit or quota exceeded: {detail[:300]}. Check your API key and billing."}
            elif e.code == 404:
                return {"error": f"Model '{self.model}' not found at Gemini API. Use /model to set a valid model name (e.g., gemini-2.0-flash)."}
            return {"error": f"Gemini API error {e.code}: {detail[:300]}"}
        except urllib.error.URLError as e:
            return {"error": f"Connection error: {e.reason}. Check your /endpoint setting."}
        except Exception as e:
            return {"error": f"Gemini API error: {str(e)}"}
        finally:
            self._stop_loading()

    def _normalize_gemini_response(self, raw: Dict) -> Dict:
        """Normalize Gemini API response to Ollama format"""
        try:
            # Check for error in response
            if "error" in raw:
                err = raw["error"]
                if isinstance(err, dict):
                    return {"error": f"Gemini API error: {err.get('message', str(err))}"}
                return {"error": f"Gemini API error: {str(err)}"}

            candidates = raw.get("candidates", [])
            if not candidates:
                prompt_feedback = raw.get("promptFeedback", {})
                block_reason = prompt_feedback.get("blockReason", "")
                if block_reason:
                    return {"error": f"Gemini blocked the request. Reason: {block_reason}"}
                return {"error": "No response candidates returned from Gemini API."}

            candidate = candidates[0]
            content_obj = candidate.get("content", {})
            parts = content_obj.get("parts", [])

            text_parts = []
            tool_calls = []

            for part in parts:
                if "text" in part:
                    text_parts.append(part["text"])
                elif "functionCall" in part:
                    fc = part["functionCall"]
                    args = fc.get("args", {})
                    if not isinstance(args, dict):
                        args = {}
                    tool_calls.append({
                        "function": {
                            "name": fc.get("name", ""),
                            "arguments": args
                        }
                    })

            content = "".join(text_parts)

            return {
                "message": {
                    "content": content,
                    "tool_calls": tool_calls if tool_calls else None
                }
            }
        except (IndexError, KeyError, TypeError) as e:
            return {"error": f"Failed to parse Gemini response: {str(e)}"}

    def _extract_code_blocks_with_files(self, content: str) -> List[Dict[str, str]]:
        """Extract code blocks that reference file paths and should be written"""
        import re

        files_to_write = []

        # Pattern 1: Code blocks with file path like "```path/to/file.cs" or "```cs # file.cs"
        pattern1 = r'```(?:\w*)\s*(?:#\s*)?(\S+\.(?:cs|py|js|ts|jsx|tsx|java|go|rs|json|xml|xaml|html|css|md|sh|ps1|config|yaml|yml))\s*\n([\s\S]*?)```'
        for match in re.finditer(pattern1, content):
            file_path = match.group(1).strip()
            code_content = match.group(2).strip()
            files_to_write.append({"path": file_path, "content": code_content})

        # Pattern 2: Look for file references in preceding lines (up to 5 lines before code block)
        lines = content.split('\n')
        pending_file = None
        current_file = None
        current_code = []
        in_code_block = False
        code_block_lang = None

        file_extensions = r'(?:cs|py|js|ts|jsx|tsx|java|go|rs|json|xml|xaml|html|css|md|sh|ps1|config|yaml|yml)'

        for i, line in enumerate(lines):
            # Check for file references (more flexible patterns)
            # Match: "MainWindow.xaml", 'MainWindow.xaml`, MainWindow.xaml:, for MainWindow.xaml, etc.
            file_patterns = [
                rf'`([^`]+\.{file_extensions})`',  # `filename.xaml`
                rf'"([^"]+\.{file_extensions})"',   # "filename.xaml"
                rf"'([^']+\.{file_extensions})'",  # 'filename.xaml'
                rf'for\s+(\S+\.{file_extensions})',  # for MainWindow.xaml
                rf'(?:in|to|into)\s+(\S+\.{file_extensions})',  # in MainWindow.xaml
                rf'(\S+\.{file_extensions}):',  # MainWindow.xaml:
            ]

            for pattern in file_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match and not in_code_block:
                    pending_file = match.group(1).strip()
                    break

            # Check if we're entering a code block
            if line.strip().startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    current_code = []
                    # Extract language from opening fence
                    lang_match = re.match(r'```(\w+)', line.strip())
                    code_block_lang = lang_match.group(1) if lang_match else None
                    # Use pending file if we found one
                    current_file = pending_file
                    pending_file = None
                else:
                    # Exiting code block
                    in_code_block = False
                    if current_file and current_code:
                        file_path = current_file
                        file_content = '\n'.join(current_code).strip()
                        if not any(f["path"] == file_path for f in files_to_write):
                            files_to_write.append({"path": file_path, "content": file_content})
                    current_file = None
                    code_block_lang = None
            elif in_code_block:
                current_code.append(line)

        # Pattern 3: Explicit "write to file" statements with code blocks
        write_pattern = r'(?:write|create|update|save|modify)\s+(?:the\s+)?(?:file\s+)?(?:at\s+)?(?:path\s+)?["\']?(\S+\.(?:cs|py|js|ts|jsx|tsx|java|go|rs|json|xml|xaml|html|css|md|sh|ps1|config|yaml|yml))["\']?\s*(?:with|:|to)(?:\s+the\s+following)?\s*(?:code|content)?[:\s]*\n```\w*\s*\n([\s\S]*?)```'
        for match in re.finditer(write_pattern, content, re.IGNORECASE):
            file_path = match.group(1).strip()
            code_content = match.group(2).strip()
            if not any(f["path"] == file_path for f in files_to_write):
                files_to_write.append({"path": file_path, "content": code_content})

        # Pattern 4: ### filepath ### followed by content (our new format)
        hash_pattern = r'###\s*(\S+\.(?:cs|py|js|ts|jsx|tsx|java|go|rs|json|xml|xaml|html|css|md|sh|ps1|config|yaml|yml))\s*###\s*\n```\w*\s*\n([\s\S]*?)```'
        for match in re.finditer(hash_pattern, content, re.IGNORECASE):
            file_path = match.group(1).strip()
            code_content = match.group(2).strip()
            if not any(f["path"] == file_path for f in files_to_write):
                files_to_write.append({"path": file_path, "content": code_content})

        # Clean up paths: strip leading /
        for f in files_to_write:
            f["path"] = f["path"].lstrip('/')

        # Deduplicate: prefer longer paths (with directories) over bare filenames
        # e.g., keep "utils/ExcelUtils.cs" over "ExcelUtils.cs"
        seen_basenames = {}
        for f in files_to_write:
            basename = Path(f["path"]).name
            if basename in seen_basenames:
                # Keep the entry with the longer path (includes directory)
                if len(f["path"]) > len(seen_basenames[basename]["path"]):
                    seen_basenames[basename] = f
            else:
                seen_basenames[basename] = f

        files_to_write = list(seen_basenames.values())

        return files_to_write

    def _pre_analyze_user_intent(self, user_input: str) -> Dict[str, Any]:
        """Pre-analyze user input to identify intent and relevant files"""
        analysis = {
            "intent": "general",
            "relevant_files": [],
            "needs_file_modification": False,
            "file_keywords": []
        }

        # Detect file modification intent
        modification_keywords = [
            'add', 'create', 'update', 'write', 'modify', 'change', 'edit', 'insert',
            'remove', 'delete', 'move', 'rename', 'implement', 'fix', 'enhance',
            'show', 'display', 'dialog', 'before', 'after', 'when', 'if'
        ]

        # Detect file types and specific file references
        file_patterns = [
            (r'\.cs(?:proj|xaml)?', 'csharp'),
            (r'\.py', 'python'),
            (r'\.js', 'javascript'),
            (r'\.ts', 'typescript'),
            (r'\.json', 'json'),
            (r'\.xml', 'xml'),
            (r'\.xaml', 'xaml'),
            (r'\.html?', 'html'),
            (r'\.css', 'css'),
            (r'\.md', 'markdown'),
            (r'\.yaml', 'yaml'),
            (r'\.yml', 'yaml'),
            (r'\.sh', 'shell'),
            (r'\.ps1', 'powershell'),
        ]

        user_lower = user_input.lower()

        # Check for modification intent
        if any(kw in user_lower for kw in modification_keywords):
            analysis["needs_file_modification"] = True
            analysis["intent"] = "modification"

        # Check for delete/remove intent specifically
        delete_keywords = ['remove', 'delete', 'rm ', 'rm file', 'del ']
        if any(kw in user_lower for kw in delete_keywords):
            analysis["intent"] = "delete"
            analysis["needs_file_modification"] = True

        # Detect specific file types mentioned
        for pattern, file_type in file_patterns:
            if re.search(pattern, user_lower):
                analysis["file_keywords"].append(file_type)

        # Detect specific file names (e.g., MainWindow, Program, App)
        specific_files = ['main', 'window', 'program', 'app', 'controller', 'model',
                         'view', 'service', 'util', 'config', 'setting', 'dialog']

        for sf in specific_files:
            if sf in user_lower:
                analysis["file_keywords"].append(sf)

        # Find relevant files from the project
        files = self._get_file_list()
        for file_path in files:
            file_lower = file_path.lower()
            # Match by keyword or extension
            if any(kw in file_lower for kw in analysis["file_keywords"]):
                analysis["relevant_files"].append(file_path)

        return analysis

    def _process_response(self, response: Dict) -> tuple[str, bool]:
        """Process Ollama response, handle tool calls recursively"""
        if "error" in response:
            return response["error"], False

        message = response.get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls", [])

        if not content and not tool_calls:
            return "Model returned empty response. Please try again.", False

        if tool_calls:
            # Sort tool calls: create directories before writing files
            TOOL_PRIORITY = {
                "create_directory": 1,
                "file_exists": 2,
                "search_files": 2,
                "list_files": 2,
                "read_file": 2,
                "run_command": 2,
                "write_file": 3,
                "delete_file": 3,
                "scaffold_project": 3,
            }
            tool_calls = sorted(tool_calls, key=lambda tc: TOOL_PRIORITY.get(
                tc.get("function", {}).get("name", ""), 4))

            results = []
            for tool_call in tool_calls:
                func = tool_call.get("function", {})
                tool_name = func.get("name", "")
                arguments = func.get("arguments", {})

                # Parse arguments if they come as a JSON string
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except (json.JSONDecodeError, TypeError):
                        arguments = {}

                # Ensure arguments is a dict
                if not isinstance(arguments, dict):
                    arguments = {}

                # Normalize alternative parameter names → 'path'
                for alt in ["file_path", "filepath", "filename", "dest", "destination"]:
                    if alt in arguments and "path" not in arguments:
                        arguments["path"] = arguments[alt]

                # Normalize alternative parameter names → 'content'
                for alt in ["contents", "data", "text", "body", "code"]:
                    if alt in arguments and "content" not in arguments:
                        arguments["content"] = arguments[alt]

                if self.show_explanation:
                    print(f"\n  \033[34m[Tool: {tool_name}]\033[0m")

                # For write_file, show diff and ask confirmation before executing
                if tool_name == "write_file":
                    file_path = arguments.get("path", "")
                    new_content = arguments.get("content", "")
                    # Replace placeholder namespaces in displayed content
                    new_content = self._replace_placeholder_namespaces(new_content)
                    arguments["content"] = new_content

                    # Validate: empty path — try to infer from content and created dirs
                    if not file_path.strip():
                        inferred = self._infer_file_path(new_content)
                        if inferred:
                            file_path = inferred
                            arguments["path"] = file_path
                        else:
                            hint = "Use format: {\"path\": \"utils/ExcelUtils.cs\", \"content\": \"...\"}"
                            if self._created_dirs:
                                dirs = ", ".join(self._created_dirs)
                                hint += f". Available directories: {dirs}. Use path like '{self._created_dirs[0]}/YourFile.cs'"
                            result = f"Error: write_file requires a 'path' argument. {hint}"

                    # Proceed with diff/confirmation if we have a valid path
                    if file_path.strip():
                        # Fix directory casing to match existing filesystem
                        fixed = self._fix_path_casing(file_path)
                        if fixed != file_path:
                            file_path = fixed
                            arguments["path"] = file_path

                        # Smart path: if bare filename with no directory, try matching created dirs
                        if not os.path.dirname(file_path) and self._created_dirs:
                            filename = Path(file_path).stem
                            for created_dir in self._created_dirs:
                                dir_name = Path(created_dir).name
                                if filename.lower().startswith(dir_name.lower()) or dir_name.lower() in filename.lower():
                                    file_path = os.path.join(created_dir, file_path)
                                    arguments["path"] = file_path
                                    break

                        resolved_path = self._resolve_path(file_path)

                        # Validate: path must not be a directory
                        if resolved_path.exists() and resolved_path.is_dir():
                            result = f"Error: '{file_path}' is a directory. Specify the full file path."
                        elif str(resolved_path) in self._files_written:
                            # Skip if already written in this request (prevent duplicates)
                            result = f"Skipped duplicate write: {file_path}"
                        else:
                            # Read existing content for diff
                            existing_content = ""
                            if resolved_path.exists():
                                try:
                                    with open(resolved_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        existing_content = f.read()
                                except:
                                    pass

                            # Show diff before writing
                            self._show_diff(existing_content, new_content, file_path)

                            # Ask for confirmation
                            print(f"\n  \033[33mApply changes to {file_path}?\033[0m")
                            confirm = input("  [y/n]: ").strip().lower()
                            if confirm == 'y':
                                result = self._execute_tool(tool_name, arguments)
                                self._files_written.add(str(resolved_path))
                            else:
                                result = f"Write cancelled by user: {file_path}"
                else:
                    result = self._execute_tool(tool_name, arguments)

                results.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call.get("id", ""),
                    "name": tool_call.get("function", {}).get("name", "")
                })

            # Continue conversation with tool results
            assistant_msg = dict(message)
            assistant_msg["role"] = "assistant"
            self.conversation_history.append(assistant_msg)
            for r in results:
                self.conversation_history.append(r)

            # Check if this was a delete operation - suppress any AI response after delete
            has_delete = any(tool_call.get("function", {}).get("name", "") == "delete_file" for tool_call in tool_calls)
            if has_delete:
                # Don't call AI again after delete - just return success
                return "", True

            # Recursive call to continue conversation with tool results
            response = self._call_api(self.conversation_history, TOOLS)
            return self._process_response(response)

        # Auto-detect code blocks that should be written to files
        files_to_write = self._extract_code_blocks_with_files(content)

        # Filter out files already written by tool calls (by full path and by filename)
        written_basenames = {Path(p).name for p in self._files_written}
        files_to_write = [f for f in files_to_write
                          if str(self._resolve_path(f["path"])) not in self._files_written
                          and Path(f["path"]).name not in written_basenames]

        if files_to_write:
            if self.show_explanation:
                print("\n  \033[34m[Auto-detecting files to write...]\033[0m")

            # Filter out files that don't exist and aren't clearly intended to be created
            # Also filter out obviously wrong extractions (like single letters before extension)
            filtered_files = []
            for f in files_to_write:
                file_path = f["path"]
                resolved = self._resolve_path(file_path)
                # Skip if filename is just a single letter before extension (like w.xaml)
                base_name = Path(file_path).stem
                if len(base_name) == 1 and resolved.exists() is False:
                    if self.show_explanation:
                        print(f"  \033[34m[Skipping likely invalid file: {file_path}]\033[0m")
                    continue
                filtered_files.append(f)
            files_to_write = filtered_files

            # Auto-read existing files first to preserve content
            files_to_write = self._auto_read_existing_files(files_to_write)

            # Process each file with individual confirmation
            for file_info in files_to_write:
                file_path = file_info["path"]
                resolved_path = self._resolve_path(file_path)
                existing = ""
                if resolved_path.exists():
                    try:
                        with open(resolved_path, 'r') as f:
                            existing = f.read()
                    except:
                        pass
                self._show_diff(existing, file_info["content"], file_path)

                # Ask for each file individually
                print(f"\n  \033[33mUpdate {file_path}?\033[0m")
                response = input("  [y/n]: ").strip().lower()
                if response == 'y':
                    result = self._execute_tool("write_file", {
                        "path": str(resolved_path),
                        "content": file_info["content"]
                    })
                else:
                    print(f"  \033[33mSkipped {file_path}\033[0m")

            # After file operations, suppress ALL AI response content
            self.conversation_history.append({"role": "assistant", "content": content})
            return "", True

        # Remove reasoning block and XML tool tags from display content
        import re
        display_content = re.sub(r'<reasoning>.*?</reasoning>', '', content, flags=re.DOTALL).strip()
        # Remove XML-style tool call blocks
        display_content = re.sub(r'<execute_tool>.*?</execute_tool>', '', display_content, flags=re.DOTALL).strip()
        display_content = re.sub(r'<tool_name>.*?</tool_name>', '', display_content, flags=re.DOTALL).strip()
        display_content = re.sub(r'<parameters>.*?</parameters>', '', display_content, flags=re.DOTALL).strip()

        self.conversation_history.append({"role": "assistant", "content": content})
        return display_content, True

    def _show_diff(self, old_content: str, new_content: str, file_path: str) -> None:
        """Show a simple diff between old and new content with line numbers"""
        old_lines = old_content.splitlines() if old_content else []
        new_lines = new_content.splitlines()

        print(f"\n  \033[36mDiff for {file_path}:\033[0m")
        print("  " + "="*60)

        # Simple line-by-line comparison
        max_lines = max(len(old_lines), len(new_lines))
        shown_changes = 0
        max_changes = 20  # Limit output

        for i in range(max_lines):
            if shown_changes >= max_changes:
                print("  ... (more changes truncated) ...")
                break

            old_line = old_lines[i] if i < len(old_lines) else None
            new_line = new_lines[i] if i < len(new_lines) else None

            if old_line != new_line:
                shown_changes += 1
                line_num = i + 1  # 1-based line numbering
                if old_line is not None and new_line is not None:
                    print(f"  \033[31m- Line {line_num:4d}: {old_line[:75]}\033[0m")
                    print(f"  \033[32m+ Line {line_num:4d}: {new_line[:75]}\033[0m")
                elif old_line is None:
                    print(f"  \033[32m+ Line {line_num:4d}: {new_line[:75]}\033[0m")
                else:
                    print(f"  \033[31m- Line {line_num:4d}: {old_line[:75]}\033[0m")

        print("  " + "="*60)

    def _ask_confirmation(self, files_to_write: List[Dict[str, str]]) -> bool:
        """Ask user for confirmation before writing files"""
        print("\n  \033[33mThe following changes will be made:\033[0m")

        for file_info in files_to_write:
            file_path = self._resolve_path(file_info["path"])
            print(f"    - {file_path}")

        print("\n  \033[33mExecute changes?\033[0m")
        print("    \033[32my\033[0m = yes (this time)")
        print("    \033[32mY\033[0m = yes (always)")
        print("    \033[31mn\033[0m = no (cancel)")

        try:
            while True:
                response = input("  [y/Y/n]: ").strip().lower()
                if response == 'y':
                    return True
                elif response == 'Y':
                    return True
                elif response == 'n':
                    return False
                else:
                    print("  Please enter y, Y, or n")
        except (KeyboardInterrupt, EOFError):
            print("\n  Cancelled.")
            return False

    def _auto_read_existing_files(self, files_to_write: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Read existing files before updating them to preserve existing code"""
        enhanced_files = []

        for file_info in files_to_write:
            file_path = self._resolve_path(file_info["path"])

            if file_path.exists():
                # Read existing content
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        existing_content = f.read()

                    # Add existing content context to the new content
                    # This helps the AI merge changes properly
                    if self.show_explanation:
                        print(f"  \033[34m[Read existing file: {file_path}]\033[0m")

                    # Merge: use new content but AI can reference existing structure
                    # The AI already has the full context, so we just write the new content
                    # which should be the complete updated version
                    enhanced_files.append(file_info)

                except Exception as e:
                    if self.show_explanation:
                        print(f"  \033[34m[Warning: Could not read {file_path}: {e}]\033[0m")
                    enhanced_files.append(file_info)
            else:
                enhanced_files.append(file_info)

        return enhanced_files

    def chat(self, user_input: str) -> str:
        """Process user input and return response - Claude Code style"""
        # Track total time for this request
        start_time = time.time()

        # Clear conversation history for fresh context each time
        self.conversation_history.clear()
        # Reset files written tracker for each request
        self._files_written = set()
        self._created_dirs = []

        # ALWAYS refresh file list and read ALL file contents for every prompt
        # Only show analysis messages if explanations are enabled
        if self.show_explanation:
            print("\n\033[34m[Analyzing project: Reading all files recursively...]\033[0m")
        files_content = self._read_all_files_contents()
        if self.show_explanation:
            print(f"\033[34m[Project Analysis Complete: {len(files_content)} files read]\033[0m")

        # Pre-analyze user intent
        intent = self._pre_analyze_user_intent(user_input)

        # Build context with file tree and ONLY relevant file contents
        files = self._get_file_list()

        context_parts = []
        context_parts.append(f"[FILE TREE - {len(files)} files]")
        for f in files[:80]:
            context_parts.append(f"  {f}")
        if len(files) > 80:
            context_parts.append(f"  ... and {len(files) - 80} more")

        context_parts.append("\n[RELEVANT FILE CONTENTS]")
        context_parts.append("=" * 50)

        # Include relevant files with full content
        for fp in intent['relevant_files'][:10]:
            if fp in files_content:
                context_parts.append(f"\n###{fp}###")
                context_parts.append(files_content[fp])

        # Include a few other project files for context
        count = len(intent['relevant_files'])
        for fp in files:
            if fp not in intent['relevant_files'] and fp in files_content and count < 15:
                context_parts.append(f"\n###{fp}###")
                context_parts.append(files_content[fp])
                count += 1

        full_context = "\n".join(context_parts)

        # Add intent information to help the AI understand what to do
        intent_hint = ""
        if intent["intent"] == "delete":
            intent_hint = "\nDETECTED INTENT: User wants to DELETE/REMOVE a file. Use the delete_file tool."

        # Build system content using string concatenation to avoid f-string issues with braces
        system_content = (
            "You are a coding assistant. You have the complete project files below." + intent_hint + "\n\n"
            "User request: " + user_input + "\n\n"
            + full_context + "\n\n"
            + "RESPOND IN THIS EXACT FORMAT:\n\n"
            + "1. First write your REASONING in a <reasoning> block:\n"
            + "<reasoning>\n"
            + "- What files exist in this project\n"
            + "- What the user wants based on those files\n"
            + "- Which specific file(s) need to be created or modified\n"
            + "- What code changes are needed\n"
            + "</reasoning>\n\n"
            + "2. Then write the COMPLETE file content in a code block with the file path:\n"
            + "```path/to/file.cs\n"
            + "// COMPLETE file content here - include ALL code, not just the changed part\n"
            + "```\n\n"
            + "CRITICAL RULES:\n"
            + "- EXACT SPECIFICATIONS: Use EXACTLY the folder names, file names, class names, and method names the user specifies\n"
            + "- PRESERVE EXACT CASING: If user says 'utils', use 'utils' NOT 'Utils'. If user says 'Utils', use 'Utils' NOT 'utils'.\n"
            + "- If user says 'utils folder', create a folder named 'utils' (NOT 'Utilities', 'Utils', 'util', etc.)\n"
            + "- If the folder ALREADY EXISTS in the FILE TREE, use its EXACT name and casing from the FILE TREE\n"
            + "- NEVER capitalize or change casing of folder/file names - use EXACTLY what user specifies or what exists in FILE TREE\n"
            + "- If user says 'ExcelUtils.cs', create a file named 'ExcelUtils.cs' (NOT 'DataUtility.cs', 'ExcelUtil.cs', etc.)\n"
            + "- If user says 'read' method, name it 'read' (NOT 'ReadExcel', 'ReadData', 'ExportToExcel', etc.)\n"
            + "- If user says 'write' method, name it 'write' (NOT 'WriteExcel', 'SaveData', 'ExportDataTable', etc.)\n"
            + "- DO NOT rename, reorganize, or reinterpret what the user asks for - follow EXACTLY what they specify\n"
            + "- Use ONLY the file content provided above - DO NOT invent or hallucinate namespaces, class names, or properties\n"
            + "- NEVER use placeholder names like 'YourAppName', 'YourNamespace', 'YourProjectNamespace', 'MyApp', 'App' etc.\n"
            + "- ALWAYS use the ACTUAL namespace/project name from the existing files in the FILE TREE\n"
            + "- For C# WPF: Look at existing .xaml and .xaml.cs files to find the ACTUAL x:Class value (e.g. 'SkyKSolution.MainWindow')\n"
            + "- When editing existing files, keep ALL original code exactly the same except for the requested change\n"
            + "- Example: If user says 'change Click Me to Click Here in MainWindow.xaml', only change that text, nothing else\n"
            + "- Example: Keep the original x:Class namespace exactly as shown in the file above\n"
            + "- Example: Keep original Height, Width, and all other properties exactly as shown\n"
            + "- ALWAYS provide the COMPLETE file content, never just partial snippets\n"
            + "- Include ALL imports, declarations, methods, and closing tags\n"
            + '- DO NOT use "// ... existing code ..." or similar placeholders\n'
            + "- DO NOT ask questions - you can see all files above\n"
            + "- DO NOT say 'I need more context' - you HAVE the context\n"
            + "- ALWAYS identify specific files from the project\n"
            + "- If you write code in a code block, it WILL be written to that file\n"
            + "- Assume the project's language (C# if .cs files, Python if .py files, etc.)\n"
            + "- ANALYZE the project files above to understand existing code structure before making changes\n"
            + "- SEARCH the FILE TREE above to find if the file already exists before creating\n"
            + "- If user mentions 'ExcelUtils.cs', search the file tree for it - it may be in a subfolder\n"
            + "- USE TOOL CALLS - do not output XML tags or text representations of tools\n"
            + "- After reading a file with read_file, you MUST call write_file to save changes\n"
            + "- NEVER invent file paths like /Users/user/Documents/... - use paths from FILE TREE\n"
            + "- After making tool calls, do NOT explain what you did or summarize the result - the tool output already shows success/failure\n"
            + "- NEVER say 'I have created...', 'The file has been written...', 'Successfully...', etc. after tool calls\n"
            + "- Just call the tools and stop - no commentary needed\n\n"
            + "FILE CREATION RULES:\n"
            + "- First check if the file already exists in the project files listed above\n"
            + "- If creating a NEW file, provide COMPLETE WORKING implementation with all necessary code\n"
            + "- DO NOT write shell commands like 'dotnet add package' - write actual code only\n"
            + "- DO NOT write package installation commands - write the actual class implementation\n"
            + "- For C# files, include proper namespace, using statements, and complete class implementation\n"
            + "- The code must be compilable/runnable - not just a placeholder or command\n"
            + "- .xaml files contain XAML markup only. .xaml.cs files contain C# code-behind only. NEVER put XAML in .cs files or C# in .xaml files\n\n"
            + "LANGUAGE-SPECIFIC NAMING RULES:\n"
            + "- C#: Class name MUST match file name (e.g., File 'ExcelUtils.cs' MUST contain 'public class ExcelUtils' or 'public static class ExcelUtils')\n"
            + "- Java: Class name MUST match file name and use PascalCase (e.g., File 'MyClass.java' MUST contain 'public class MyClass')\n"
            + "- Python: Use snake_case for file names and PascalCase for class names (e.g., File 'my_utils.py' contains 'class MyUtils:')\n"
            + "- JavaScript/TypeScript: Use PascalCase for class names that match the file name (e.g., File 'UserService.js' contains 'class UserService')\n\n"
            + "AVAILABLE TOOLS:\n"
            + "- create_directory: Create a new directory (MUST be called BEFORE write_file for new folders)\n"
            + "- read_file: Read a file's content (use full path from FILE TREE)\n"
            + "- write_file: Write content to a file. ALWAYS include 'path' and 'content' arguments.\n"
            + "- search_files: Search for files using glob patterns like '**/*.cs' (WITH 's' at end)\n"
            + "- file_exists: Check if a file or directory exists\n"
            + "- delete_file: Delete a file\n"
            + "- run_command: Execute a shell command\n"
            + "- list_files: List files in a directory\n"
            + "- scaffold_project: Create a new project from template\n\n"
            + "TOOL CALL ORDER - MANDATORY:\n"
            + "When creating files in new directories, you MUST call tools in this order:\n"
            + "  1. create_directory (for the parent folder) FIRST\n"
            + "  2. write_file (with the full path including the folder) SECOND\n"
            + "Example: 'create utils/ExcelUtils.cs' means:\n"
            + "  Step 1: create_directory path='utils'\n"
            + "  Step 2: write_file path='utils/ExcelUtils.cs' content='...'\n"
            + "NEVER call write_file without a 'path' argument.\n"
            + "NEVER call create_directory for the same directory twice.\n\n"
            + "WRITE FILE OPERATIONS - MANDATORY:\n"
            + "STEP 1: Search for file using search_files (with 's' at end) tool with pattern '**/*filename' to find it in any subfolder\n"
            + "STEP 2: If file EXISTS: use read_file tool with the full path found\n"
            + "STEP 3: If file EXISTS: analyze the content and determine what to update\n"
            + "STEP 4: If file EXISTS: use write_file tool to write complete updated content\n"
            + "STEP 5: If file does NOT exist: use write_file tool to create new file\n"
            + "DO NOT output code blocks directly - ALWAYS use the tools\n"
            + "DO NOT output XML tags like <execute_tool> - use actual tool calls\n"
            + "USE search_files (with 's' at end) with pattern '**/Filename.cs' to search ALL subdirectories\n"
            + "IMPORTANT: Tool name is search_files not search_file - always include the 's'\n"
            + "After search_files returns results, use the FULL FILE PATH from results to read the file\n"
            + "USE ONLY the file paths from the FILE TREE or search_results - do not invent paths\n\n"
            + "DELETE OPERATIONS - IMPORTANT:\n"
            + '- When user says "remove", "delete", "rm", or "remove file", you MUST use the delete_file tool\n'
            + '- DO NOT just say "I have removed the file" - actually call the delete_file tool\n'
            + '- Example: "remove utils/ExcelUtils.cs" -> use delete_file tool with path="utils/ExcelUtils.cs"\n'
            + '- Example: "delete the file test.txt" -> use delete_file tool with path="test.txt"\n'
            + "- First check if file exists with file_exists, then delete it with delete_file"
        )

        self.conversation_history.append({"role": "system", "content": system_content})
        self.conversation_history.append({"role": "user", "content": user_input})

        # Don't use TOOLS with gemma models - they don't support tool calling well
        # But allow specific tools for gemma that are needed for basic operations
        # Online models (OpenAI and Gemini) always support tool calling
        if self.provider in ("openai", "gemini", "groq"):
            tools_to_use = TOOLS
        elif self.model.startswith("gemma"):
            gemma_allowed = ["scaffold_project", "delete_file", "file_exists", "read_file", "write_file", "list_files", "search_files"]
            tools_to_use = [t for t in TOOLS if t["function"]["name"] in gemma_allowed]
        else:
            tools_to_use = TOOLS

        # Debug: show which tools are being used
        if self.show_explanation:
            tool_names = [t["function"]["name"] for t in tools_to_use]
            provider_label = f"[{self.provider}]" if self.provider != "ollama" else ""
            print(f"\033[34m[Tools available: {', '.join(tool_names)}] {provider_label}\033[0m")

        # Early check for online provider requirements
        if self.provider in ("openai", "gemini", "groq") and not self.api_key:
            return ("No API key set for online provider.\n"
                    "Use /key <your-api-key> to set one.\n"
                    "Or switch to offline mode with: /provider ollama")

        response = self._call_api(self.conversation_history, tools_to_use)
        content, success = self._process_response(response)

        if not success:
            self.conversation_history.pop()
            self.conversation_history.pop()

        # Show total time taken
        elapsed = time.time() - start_time
        if elapsed < 60:
            print(f"\n\033[90mDone in {elapsed:.1f}s\033[0m")
        else:
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            print(f"\n\033[90mDone in {mins}m {secs}s\033[0m")

        return content

    def handle_slash_command(self, command: str) -> str:
        """Handle slash commands"""
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/init":
            return self._cmd_init(args)
        elif cmd == "/model":
            return self._cmd_model(args)
        elif cmd == "/provider":
            return self._cmd_provider(args)
        elif cmd == "/key":
            return self._cmd_key(args)
        elif cmd == "/endpoint":
            return self._cmd_endpoint(args)
        elif cmd == "/resume":
            return self._cmd_resume(args)
        elif cmd == "/btw":
            return self._cmd_btw(args)
        elif cmd == "/toggle":
            self.show_explanation = not self.show_explanation
            return f"Explanation display: {'ON' if self.show_explanation else 'OFF'}"
        elif cmd == "/help":
            return self._cmd_help()
        elif cmd == "/clear":
            self.conversation_history.clear()
            return "Conversation history cleared."
        elif cmd == "/config":
            return self._cmd_config(args)
        elif cmd == "/tools":
            return self._cmd_tools()
        elif cmd == "/history":
            return self._cmd_history(args)
        elif cmd == "/scaffold":
            return self._cmd_scaffold(args)
        elif cmd == "/templates":
            return self._cmd_templates()
        elif cmd == "/explain":
            return self._cmd_explain(args)
        elif cmd == "/fix":
            return self._cmd_fix(args)
        elif cmd == "/test":
            return self._cmd_test(args)
        elif cmd == "/summarize":
            return self._cmd_summarize(args)
        elif cmd == "/uninstall":
            return self._cmd_uninstall(args)
        elif cmd == "/files":
            return self._cmd_files(args)
        else:
            return f"Unknown command: {cmd}. Use /help for available commands."

    def _cmd_init(self, args: str) -> str:
        """Analyze project and create/update ACAT.md"""
        print("Analyzing project structure...")

        project_info = {
            "name": self.working_dir.name,
            "path": str(self.working_dir),
            "analyzed_at": datetime.now().isoformat(),
            "structure": [],
            "files": [],
            "tech_stack": []
        }

        # Analyze directory structure recursively
        def walk_dir(path, prefix=""):
            items = []
            dirs = []
            for item in sorted(path.iterdir()):
                if item.name.startswith('.') or item.name == '__pycache__':
                    continue
                if item.is_dir():
                    dirs.append(item)
                else:
                    items.append(item)

            # Add directories first
            for d in dirs:
                items.append(d)

            for i, item in enumerate(items):
                is_last = (i == len(items) - 1)
                marker = "└── " if is_last else "├── "
                next_prefix = prefix + "    " if is_last else prefix + "│   "

                if item.is_file():
                    project_info["structure"].append(f"{prefix}{marker}{item.name}")
                    # Track root-level files
                    if path == self.working_dir:
                        project_info["files"].append(item.name)
                else:
                    project_info["structure"].append(f"{prefix}{marker}{item.name}/")
                    try:
                        walk_dir(item, next_prefix)
                    except PermissionError:
                        pass

        walk_dir(self.working_dir)

        # Detect tech stack (search recursively)
        if list(self.working_dir.rglob("package.json")):
            project_info["tech_stack"].append("Node.js/JavaScript")
        if list(self.working_dir.rglob("requirements.txt")):
            project_info["tech_stack"].append("Python")
        if list(self.working_dir.rglob("pom.xml")):
            project_info["tech_stack"].append("Java/Maven")
        if list(self.working_dir.rglob("build.gradle")):
            project_info["tech_stack"].append("Java/Gradle")
        if list(self.working_dir.rglob("Cargo.toml")):
            project_info["tech_stack"].append("Rust")
        if list(self.working_dir.rglob("go.mod")):
            project_info["tech_stack"].append("Go")
        if list(self.working_dir.rglob("*.csproj")):
            project_info["tech_stack"].append("C#/.NET")
        if list(self.working_dir.rglob("index.html")):
            project_info["tech_stack"].append("Static Web")

        acat_content = f"""# ACAT.md - Project Context for AI Assistant

## Project Overview

**Name:** {project_info['name']}
**Path:** {project_info['path']}
**Last Analyzed:** {project_info['analyzed_at']}

## Technology Stack

{chr(10).join('- ' + t for t in project_info['tech_stack']) or '- Not yet detected'}

## Directory Structure

{chr(10).join(project_info['structure']) or '- No subdirectories'}

## Key Files

{chr(10).join('- ' + f for f in project_info['files']) or '- No files in root'}

## Development Setup

<!-- Add setup instructions here -->

## Commands

<!-- Add common commands here -->

## Notes

<!-- Add project-specific notes here -->
"""

        acat_path = self.working_dir / ACAT_MD_FILE
        with open(acat_path, 'w') as f:
            f.write(acat_content)

        return f"Created/updated {ACAT_MD_FILE} at {acat_path}"

    def _cmd_model(self, args: str) -> str:
        """Get or set the current model"""
        if args:
            self.model = args.strip()
            self.config["model"] = self.model
            self._save_config()
            return f"Model set to: {self.model}"
        return f"Current model: {self.model}\nProvider: {self.provider}"

    def _cmd_provider(self, args: str) -> str:
        """Switch between ollama (offline), openai (online), gemini (online), and groq (online) providers"""
        if not args:
            return (f"Current provider: {self.provider}\n"
                    f"Use '/provider ollama' for offline (Ollama)\n"
                    f"Use '/provider openai' for online (OpenAI-compatible API)\n"
                    f"Use '/provider gemini' for online (Google Gemini API)\n"
                    f"Use '/provider groq' for online (Groq - fast inference)")

        provider = args.strip().lower()
        if provider not in ("ollama", "openai", "gemini", "groq"):
            return "Invalid provider. Use 'ollama', 'openai', 'gemini', or 'groq'."

        # Save current provider's credentials before switching
        self._save_provider_credentials()

        self.provider = provider
        self.config["provider"] = self.provider
        self._save_config()

        # Load new provider's saved credentials
        self._load_provider_credentials()

        if provider == "openai":
            # Only keep model if it's a known OpenAI model
            openai_models = ("gpt-", "o1-", "o3-", "chatgpt-", "dall-e")
            if not any(self.model.startswith(m) for m in openai_models):
                self.model = "gpt-4o-mini"
                self.config["model"] = self.model
                self._save_config()
            if not self.api_key:
                return (f"Provider set to: openai\n"
                        f"Model set to: {self.model}\n"
                        f"Set your API key with: /key <your-api-key>\n"
                        f"Set endpoint with: /endpoint <url> (default: {DEFAULT_API_ENDPOINT})")

        elif provider == "gemini":
            if not self.model.startswith("gemini"):
                self.model = DEFAULT_GEMINI_MODEL
                self.config["model"] = self.model
                self._save_config()
            if not self.api_key:
                return (f"Provider set to: gemini\n"
                        f"Model set to: {self.model}\n"
                        f"Set your API key with: /key <your-gemini-api-key>\n"
                        f"Get an API key at: https://aistudio.google.com/apikey")

        elif provider == "groq":
            # Only keep model if it's a known Groq model (not Ollama models like gemma4:latest)
            groq_models = ("llama-", "mixtral-", "gemma2-")
            if not any(self.model.startswith(m) for m in groq_models):
                self.model = DEFAULT_GROQ_MODEL
                self.config["model"] = self.model
                self._save_config()
            if not self.api_key:
                return (f"Provider set to: groq\n"
                        f"Model set to: {self.model}\n"
                        f"Set your API key with: /key <your-groq-api-key>\n"
                        f"Get an API key at: https://console.groq.com/keys")

        return (f"Provider set to: {self.provider}\n"
                f"Model: {self.model}")

    def _cmd_key(self, args: str) -> str:
        """Set API key for online providers"""
        if not args:
            if self.api_key:
                masked = self.api_key[:8] + "..." + self.api_key[-4:] if len(self.api_key) > 12 else "***"
                return f"Current [{self.provider}] API key: {masked}"
            return f"No API key set for {self.provider}. Use: /key <your-api-key>"

        self.api_key = args.strip()
        self._save_provider_credentials()
        masked = self.api_key[:8] + "..." + self.api_key[-4:] if len(self.api_key) > 12 else "***"
        return f"[{self.provider}] API key set: {masked}"

    def _cmd_endpoint(self, args: str) -> str:
        """Set API endpoint for online providers"""
        if not args:
            return f"Current [{self.provider}] endpoint: {self.api_endpoint}\nUse: /endpoint <url>"

        self.api_endpoint = args.strip().rstrip('/')
        self._save_provider_credentials()
        return f"[{self.provider}] API endpoint set to: {self.api_endpoint}"

    def _cmd_resume(self, args: str) -> str:
        """Resume a previous conversation or task"""
        # Load from session file if exists
        session_file = ACAT_CONFIG_DIR / "session.json"
        if session_file.exists():
            with open(session_file, 'r') as f:
                session = json.load(f)
                self.conversation_history = session.get("history", [])
                return f"Resumed session with {len(self.conversation_history)} messages."
        return "No saved session found."

    def _cmd_btw(self, args: str) -> str:
        """Add context or note to conversation"""
        if args:
            self.conversation_history.append({
                "role": "system",
                "content": f"[User note: {args}]"
            })
            return f"Noted: {args}"
        return "Usage: /btw <note or context>"

    def _cmd_files(self, args: str) -> str:
        """Show the cached file list"""
        self._refresh_file_list()
        files = self._get_file_list()
        if not files:
            return "No files found in the current directory."

        output = [f"Files in {self.working_dir}:\n"]
        for f in files:
            output.append(f"  {f}")

        output.append(f"\nTotal: {len(files)} files")
        return "\n".join(output)

    def _cmd_help(self) -> str:
        """Show available commands"""
        return """
Available Commands:
  /init              - Analyze project and create ACAT.md
  /model [name]      - Get or set the AI model
  /provider [name]   - Switch provider (ollama/openai/gemini/groq)
  /key [key]         - Set API key for online providers
  /endpoint [url]    - Set API endpoint for online providers
  /resume            - Resume previous session
  /btw <note>        - Add context/note to conversation
  /config            - Show current configuration
  /tools             - List available tools
  /history [n]       - Show last n messages (default: 10)
  /clear             - Clear conversation history
  /help              - Show this help message
  /scaffold          - Create project from template
  /templates         - List available project templates
  /explain <file>    - Explain code in a file
  /fix <file> [issue]- Find and fix issues in code
  /test <file>       - Generate tests for code
  /summarize [file]  - Summarize code or conversation
  /uninstall         - Uninstall acat CLI (keeps Ollama)
  /files             - Show cached file list (background project structure)

Uninstall Usage:
  /uninstall         - Remove acat CLI and config files
  /uninstall --clean-path - Also remove PATH entries from shell profiles

Scaffold Usage:
  /scaffold <template> <project-name> [path]
  Templates: static-web, spring-boot, wpf-csharp, react, react-native, electron

Keyboard Shortcuts:
  Ctrl+C         - Cancel current response
  Ctrl+D         - Exit acat
  Ctrl+L         - Clear screen
  Esc            - Exit acat (when at prompt)
"""

    def _cmd_config(self, args: str) -> str:
        """Show or update configuration"""
        if args:
            try:
                key, value = args.split("=", 1)
                self.config[key.strip()] = value.strip()
                self._save_config()
                return f"Set {key.strip()} = {value.strip()}"
            except:
                return "Usage: /config key=value"
        # Mask API keys in display
        display_config = dict(self.config)
        for key in list(display_config.keys()):
            if key.endswith("_key") and display_config[key]:
                val = display_config[key]
                display_config[key] = val[:8] + "..." + val[-4:] if len(val) > 12 else "***"
        return f"Configuration:\n{json.dumps(display_config, indent=2)}"

    def _cmd_tools(self) -> str:
        """List available tools"""
        tools_info = ["Available Tools:"]
        for tool in TOOLS:
            fn = tool["function"]
            tools_info.append(f"  - {fn['name']}: {fn['description']}")
        return "\n".join(tools_info)

    def _cmd_history(self, args: str) -> str:
        """Show conversation history"""
        n = int(args) if args else 10
        if not self.conversation_history:
            return "No conversation history."

        history = self.conversation_history[-n:]
        output = []
        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            output.append(f"[{role}]: {content}..." if len(content) > 200 else f"[{role}]: {content}")
        return "\n\n".join(output)

    def _cmd_scaffold(self, args: str) -> str:
        """Scaffold a new project"""
        if not args:
            return "Usage: /scaffold <template> <project-name> [path]\n\nAvailable templates: static-web, spring-boot, wpf-csharp, react, react-native, electron"

        parts = args.split()
        if len(parts) < 2:
            return "Usage: /scaffold <template> <project-name> [path]"

        template = parts[0]
        name = parts[1]
        dest = parts[2] if len(parts) > 2 else name

        result = self._execute_tool("scaffold_project", {
            "template": template,
            "name": name,
            "path": dest
        })
        return result

    def _cmd_templates(self) -> str:
        """List available templates"""
        templates_dir = Path(__file__).parent.parent / "templates"
        if not templates_dir.exists():
            return "Templates directory not found."

        available = [d.name for d in templates_dir.iterdir() if d.is_dir()]
        return "Available templates:\n  - " + "\n  - ".join(available)

    def _cmd_explain(self, args: str) -> str:
        """Explain code in a file"""
        if not args:
            return "Usage: /explain <file-path>"
        file_path = self._resolve_path(args.strip())
        if not file_path.exists():
            return f"Error: File not found: {file_path}"
        # Add context and let AI explain
        self.conversation_history.append({
            "role": "system",
            "content": f"User wants to understand this file: {file_path}"
        })
        return self.chat(f"Please explain the code in {file_path}:")

    def _cmd_fix(self, args: str) -> str:
        """Find and fix issues in code"""
        if not args:
            return "Usage: /fix <file-path> [description of issue]"
        parts = args.split(maxsplit=1)
        file_path = self._resolve_path(parts[0])
        issue = parts[1] if len(parts) > 1 else "any bugs or issues"
        if not file_path.exists():
            return f"Error: File not found: {file_path}"
        self.conversation_history.append({
            "role": "system",
            "content": f"User wants to fix {issue} in: {file_path}"
        })
        return self.chat(f"Find and fix {issue} in {file_path}. Suggest changes:")

    def _cmd_test(self, args: str) -> str:
        """Generate tests for code"""
        if not args:
            return "Usage: /test <file-path>"
        file_path = self._resolve_path(args.strip())
        if not file_path.exists():
            return f"Error: File not found: {file_path}"
        self.conversation_history.append({
            "role": "system",
            "content": f"User wants tests for: {file_path}"
        })
        return self.chat(f"Generate comprehensive tests for {file_path}:")

    def _cmd_summarize(self, args: str) -> str:
        """Summarize code or conversation"""
        if args:
            file_path = self._resolve_path(args.strip())
            if file_path.exists():
                self.conversation_history.append({
                    "role": "system",
                    "content": f"User wants summary of: {file_path}"
                })
                return self.chat(f"Summarize the contents of {file_path}:")
        # Summarize conversation
        if not self.conversation_history:
            return "No conversation to summarize."
        return self.chat("Summarize our conversation so far:")

    def _cmd_uninstall(self, args: str) -> str:
        """Uninstall acat completely (keeps Ollama and models)"""
        import shutil

        acat_dir = Path.home() / ".acat"
        bin_file = Path.home() / ".local" / "bin" / "acat"
        session_file = Path.home() / ".acat" / "session.json"
        config_file = Path.home() / ".acat" / "config.json"

        print("Uninstalling acat CLI...")
        print(f"  - Removing {acat_dir}")
        print(f"  - Removing {bin_file}")

        removed = []

        # Remove acat directory
        if acat_dir.exists():
            shutil.rmtree(acat_dir)
            removed.append(str(acat_dir))

        # Remove bin wrapper
        if bin_file.exists():
            bin_file.unlink()
            removed.append(str(bin_file))

        # Clean PATH from shell profiles (optional)
        if args == "--clean-path":
            print("  - Cleaning PATH from shell profiles...")
            for profile in [Path.home() / ".zshrc", Path.home() / ".bashrc", Path.home() / ".profile"]:
                if profile.exists():
                    try:
                        with open(profile, 'r') as f:
                            lines = f.readlines()
                        with open(profile, 'w') as f:
                            for line in lines:
                                if 'acat installer' not in line and '.local/bin' not in line:
                                    f.write(line)
                        removed.append(f"PATH entries from {profile}")
                    except Exception as e:
                        print(f"    Warning: Could not clean {profile}: {e}")

        if removed:
            print("\n✓ Uninstallation complete!")
            print("Removed:")
            for item in removed:
                print(f"  - {item}")
            print("\nNote: Ollama and its models are NOT uninstalled.")
            print("To remove Ollama separately, use: ollama --help")
        else:
            return "acat CLI not found. Nothing to uninstall."

        return "acat CLI has been uninstalled successfully."
        if not self.conversation_history:
            return "No conversation history."

        history = self.conversation_history[-n:]
        output = []
        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            output.append(f"[{role}]: {content}..." if len(content) > 200 else f"[{role}]: {content}")
        return "\n\n".join(output)

    def run_interactive(self):
        """Run interactive REPL"""
        # Banner is printed by bash wrapper, just show ready message
        provider_label = "offline" if self.provider == "ollama" else "online"
        print(f"Model: {self.model} ({self.provider}/{provider_label})")
        print(f"Working directory: {self.working_dir}")
        print()
        print("Type / for slash commands, Tab to complete.")
        print("Press Ctrl+D or Esc to quit, Ctrl+C to cancel.")
        print()

        # Available slash commands for tooltip
        slash_commands = [
            ("/init", "Analyze project and create ACAT.md"),
            ("/model [name]", "Get or set the AI model"),
            ("/provider [name]", "Switch provider (ollama/openai/gemini/groq)"),
            ("/key [key]", "Set API key for online providers"),
            ("/endpoint [url]", "Set API endpoint for online providers"),
            ("/resume", "Resume previous session"),
            ("/btw <note>", "Add context/note to conversation"),
            ("/toggle", "Toggle explanation display (Ctrl+O)"),
            ("/config", "Show current configuration"),
            ("/tools", "List available tools"),
            ("/history [n]", "Show last n messages"),
            ("/clear", "Clear conversation history"),
            ("/help", "Show this help message"),
            ("/scaffold", "Create project from template"),
            ("/templates", "List available templates"),
            ("/explain <file>", "Explain code in a file"),
            ("/fix <file>", "Find and fix issues in code"),
            ("/test <file>", "Generate tests for code"),
            ("/summarize [file]", "Summarize code or conversation"),
            ("/uninstall", "Uninstall acat CLI"),
            ("/exit", "Exit acat")
        ]

        # Track if we already showed hints for current input
        shown_hints_for = None

        def print_hint():
            """Print slash command hint - shows when user types just /"""
            print(f"\n\033[38;5;208mAvailable slash commands:\033[0m")
            for cmd, desc in slash_commands:
                print(f"  \033[38;5;208m{cmd:<20}\033[0m {desc}")
            print()

        def print_hint_for_prefix(prefix: str):
            """Print hint for slash commands matching prefix"""
            nonlocal shown_hints_for
            matches = [(cmd, desc) for cmd, desc in slash_commands if cmd.lower().startswith(prefix.lower())]
            if matches and shown_hints_for != prefix:
                print(f"\n\033[38;5;208mMatching slash commands:\033[0m")
                for cmd, desc in matches:
                    print(f"  \033[38;5;208m{cmd:<20}\033[0m {desc}")
                print()
                shown_hints_for = prefix

        def slash_completer(text, state):
            """Tab completer for slash commands - shows all matches on Tab"""
            nonlocal shown_hints_for
            if not text:
                return None
            if text.startswith('/'):
                matches = [cmd for cmd, _ in slash_commands if cmd.lower().startswith(text.lower())]
                if state == 0 and len(matches) > 1 and shown_hints_for != text:
                    print(f"\n\033[38;5;208mAvailable completions:\033[0m")
                    for cmd, desc in matches:
                        print(f"  \033[38;5;208m{cmd:<20}\033[0m {desc}")
                    shown_hints_for = text
                if state < len(matches):
                    return matches[state]
            return None

        # Use prompt_toolkit for dynamic hints while typing
        if PROMPT_TOOLKIT_AVAILABLE:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.formatted_text import HTML, to_formatted_text, FormattedText
            from prompt_toolkit.shortcuts import print_formatted_text
            from prompt_toolkit.styles import Style
            from prompt_toolkit.lexers import Lexer

            acat_style = Style.from_dict({
                'completion-menu.completion': 'bg:#ffa500 #000000',
                'completion-menu.completion.current': 'bg:#ff8800 #000000 bold',
                'prompt': '#00aa00 bold',
                'ansiorange': '#ffa500',
                'slashcommand': '#ffa500',
            })

            class SlashCommandLexer(Lexer):
                def lex_document(self, document):
                    def get_tokens(line_number):
                        text = document.text
                        if text.startswith('/'):
                            # Split on first space
                            parts = text.split(' ', 1)
                            slash_cmd = parts[0]
                            result = [('class:slashcommand', slash_cmd)]
                            if len(parts) > 1:
                                result.append(('', ' ' + parts[1]))
                            return result
                        else:
                            return [('', text)]
                    return get_tokens

            class SlashCompleter(Completer):
                def get_completions(self, document, complete_event):
                    try:
                        text = document.text_before_cursor
                        if text.startswith('/'):
                            for cmd, desc in slash_commands:
                                if cmd.lower().startswith(text.lower()):
                                    if text == cmd:
                                        continue
                                    # Use simple string display instead of FormattedText
                                    display = f'{cmd} - {desc}'
                                    yield Completion(cmd, start_position=-len(text), display=display)
                    except Exception:
                        # Fallback: yield simple completions
                        if text.startswith('/'):
                            for cmd, _ in slash_commands:
                                if cmd.lower().startswith(text.lower()):
                                    yield Completion(cmd, start_position=-len(text))

            # Key bindings for Esc (exit), Ctrl+D
            kb = KeyBindings()

            @kb.add('escape')
            def handle_escape(event):
                """Cancel current operation without exiting"""
                self.cancel_current = True
                # Don't raise EOFError - just cancel current operation

            @kb.add('c-d')
            def _(event):
                raise EOFError

            while not self.stop_flag:
                try:
                    session = PromptSession(
                        HTML('<prompt>acat></prompt> '),
                        completer=SlashCompleter(),
                        style=acat_style,
                        complete_while_typing=True,
                        key_bindings=kb,
                        lexer=SlashCommandLexer(),
                    )
                    user_input = session.prompt()
                    display_input = user_input.strip()

                    if not display_input:
                        continue

                    if display_input == "/":
                        print_hint()
                        continue

                    if display_input.startswith("/") and " " not in display_input:
                        matches = [(cmd, desc) for cmd, desc in slash_commands if cmd.lower().startswith(display_input.lower()) and cmd.lower() != display_input.lower()]
                        if matches:
                            print_hint_for_prefix(display_input)

                    user_input = display_input

                    if user_input in ("/exit", "/quit", "exit", "quit"):
                        print("Goodbye!")
                        break

                    if user_input.startswith("/"):
                        response = self.handle_slash_command(user_input)
                    else:
                        response = self.chat(user_input)

                    # Show response based on toggle
                    if self.show_explanation:
                        print(f"\n{response}")
                    else:
                        # When hidden, just show a brief confirmation
                        if user_input.startswith("/"):
                            print(f"  \033[34m[✓] Command executed (/toggle to show)\033[0m")
                        else:
                            print(f"  \033[34m[✓] Response received (/toggle to show)\033[0m")
                except KeyboardInterrupt:
                    print("\n\nInterrupted. Type /exit to quit.")
                except EOFError:
                    print("\nGoodbye!")
                    break
        else:
            # Fallback to readline (not available on Windows)
            if READLINE_AVAILABLE:
                readline.set_completer(slash_completer)
                readline.parse_and_bind("tab: complete")
                readline.parse_and_bind("set show-all-if-ambiguous on")
                readline.parse_and_bind("\\e: abort")

            while not self.stop_flag:
                try:
                    # Print prompt separately for Windows compatibility
                    sys.stdout.write(_strip_ansi("\033[92macat>\033[0m "))
                    sys.stdout.flush()
                    user_input = input()
                    display_input = user_input.strip()

                    if not display_input:
                        continue

                    if display_input == "/":
                        print_hint()
                        continue

                    if display_input.startswith("/") and " " not in display_input:
                        matches = [(cmd, desc) for cmd, desc in slash_commands if cmd.lower().startswith(display_input.lower()) and cmd.lower() != display_input.lower()]
                        if matches:
                            print_hint_for_prefix(display_input)

                    user_input = display_input

                    if user_input in ("/exit", "/quit", "exit", "quit"):
                        print("Goodbye!")
                        break

                    if user_input.startswith("/"):
                        print(f"\n\033[38;5;208m{user_input}\033[0m")
                        response = self.handle_slash_command(user_input)
                    else:
                        response = self.chat(user_input)

                    # Show response based on toggle
                    if self.show_explanation:
                        print(f"\n{response}")
                    else:
                        # When hidden, just show a brief confirmation
                        if user_input.startswith("/"):
                            print(f"  \033[34m[✓] Command executed (/toggle to show)\033[0m")
                        else:
                            print(f"  \033[34m[✓] Response received (/toggle to show)\033[0m")
                except KeyboardInterrupt:
                    print("\n\nInterrupted. Type /exit to quit.")
                except EOFError:
                    print("\nGoodbye!")
                    break

        # Save session
        session_file = ACAT_CONFIG_DIR / "session.json"
        with open(session_file, 'w') as f:
            json.dump({"history": self.conversation_history}, f)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="acat - AI CLI Agent")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help="Model to use")
    parser.add_argument("-c", "--command", help="Run single command and exit")
    parser.add_argument("--init", action="store_true", help="Initialize project")
    parser.add_argument("-v", "--version", action="store_true", help="Show version")

    args = parser.parse_args()

    if args.version:
        print("acat version 0.1.0")
        return

    agent = AcatAgent(model=args.model)

    if args.init:
        print(agent._cmd_init(""))
        return

    if args.command:
        if args.command.startswith("/"):
            print(agent.handle_slash_command(args.command))
        else:
            print(agent.chat(args.command))
        return

    agent.run_interactive()


if __name__ == "__main__":
    main()
