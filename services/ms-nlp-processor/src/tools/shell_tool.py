"""
Shell execution tool for agents.
Allows safe execution of system commands.
"""
import asyncio
import subprocess
import os
import logging
from typing import Dict, Any, List
from .base_tool import BaseTool

logger = logging.getLogger(__name__)

class ShellTool(BaseTool):
    """Tool for executing shell commands safely."""
    
    def __init__(self):
        super().__init__(
            name="shell_tool",
            description="Execute shell commands safely on the system"
        )
        
        # Define safe commands that can be executed
        self.safe_commands = [
            "ls", "pwd", "whoami", "date", "uptime", "df", "free", "ps",
            "cat", "grep", "find", "wc", "head", "tail", "sort", "uniq",
            "echo", "printf", "which", "whereis", "file", "stat", "du",
            "top", "htop", "uname", "id", "groups", "env", "history",
            "git", "python", "python3", "pip", "pip3", "node", "npm",
            "docker", "kubectl", "curl", "wget", "ping", "nslookup",
            "netstat", "ss", "lsof", "mount", "umount", "lsblk"
        ]
        
        # Dangerous commands that are explicitly blocked
        self.blocked_commands = [
            "rm", "rmdir", "mv", "cp", "chmod", "chown", "chgrp",
            "sudo", "su", "passwd", "useradd", "userdel", "usermod",
            "groupadd", "groupdel", "fdisk", "mkfs", "format", "mount",
            "umount", "kill", "killall", "pkill", "shutdown", "reboot",
            "halt", "poweroff", "init", "systemctl", "service", "crontab",
            "at", "batch", "nohup", "screen", "tmux", "iptables",
            "ufw", "firewall", "selinux", "apparmor"
        ]
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a shell command safely.
        
        Args:
            parameters: Dict containing 'command' and optional 'timeout'
            
        Returns:
            Dict containing command output, exit code, and metadata
        """
        try:
            command = parameters.get("command", "")
            timeout = parameters.get("timeout", 30)
            working_dir = parameters.get("working_dir", None)
            
            # Validate parameters
            if not self.validate_parameters(parameters):
                return {
                    "success": False,
                    "error": "Invalid parameters",
                    "output": "",
                    "exit_code": -1
                }
            
            # Check if command is safe
            if not self._is_command_safe(command):
                return {
                    "success": False,
                    "error": "Command not allowed for security reasons",
                    "output": "",
                    "exit_code": -1
                }
            
            # Execute command
            result = await self._execute_command(command, timeout, working_dir)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing shell command: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "exit_code": -1
            }
    
    def _is_command_safe(self, command: str) -> bool:
        """Check if command is safe to execute."""
        # Get the base command (first word)
        base_command = command.split()[0] if command.split() else ""
        
        # Check against blocked commands
        for blocked in self.blocked_commands:
            if base_command == blocked or command.startswith(blocked + " "):
                return False
        
        # Only allow known safe commands
        if base_command not in self.safe_commands:
            return False
        
        # Additional safety checks
        if not self.is_safe_command(command):
            return False
        
        return True
    
    async def _execute_command(self, command: str, timeout: int, working_dir: str = None) -> Dict[str, Any]:
        """Execute the command asynchronously."""
        try:
            # Set up working directory
            cwd = working_dir if working_dir and os.path.exists(working_dir) else None
            
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout} seconds",
                    "output": "",
                    "exit_code": -1
                }
            
            # Decode output
            stdout_text = stdout.decode('utf-8', errors='replace').strip()
            stderr_text = stderr.decode('utf-8', errors='replace').strip()
            
            # Combine output
            output = stdout_text
            if stderr_text:
                output += f"\n[STDERR]\n{stderr_text}"
            
            return {
                "success": process.returncode == 0,
                "output": output,
                "exit_code": process.returncode,
                "command": command,
                "working_dir": cwd,
                "timeout": timeout
            }
            
        except Exception as e:
            logger.error(f"Error in _execute_command: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "exit_code": -1
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool schema."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute safely"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds (default: 30)",
                    "default": 30
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory for command execution (optional)"
                }
            },
            "required": ["command"]
        }
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get basic system information."""
        info_commands = {
            "hostname": "hostname",
            "user": "whoami",
            "os": "uname -a",
            "uptime": "uptime",
            "disk_usage": "df -h",
            "memory": "free -h",
            "current_dir": "pwd"
        }
        
        system_info = {}
        
        for key, cmd in info_commands.items():
            try:
                result = await self.execute({"command": cmd})
                if result["success"]:
                    system_info[key] = result["output"].split('\n')[0]  # First line only
                else:
                    system_info[key] = "N/A"
            except Exception as e:
                system_info[key] = f"Error: {str(e)}"
        
        return system_info
    
    async def list_files(self, directory: str = ".", detailed: bool = False) -> Dict[str, Any]:
        """List files in a directory."""
        if detailed:
            command = f"ls -la {directory}"
        else:
            command = f"ls {directory}"
        
        return await self.execute({"command": command})
    
    async def read_file(self, filepath: str, lines: int = None) -> Dict[str, Any]:
        """Read file contents safely."""
        if lines:
            command = f"head -n {lines} {filepath}"
        else:
            command = f"cat {filepath}"
        
        return await self.execute({"command": command})
    
    async def search_in_files(self, pattern: str, directory: str = ".", file_pattern: str = "*") -> Dict[str, Any]:
        """Search for pattern in files."""
        command = f"grep -r \"{pattern}\" {directory} --include=\"{file_pattern}\""
        return await self.execute({"command": command})
