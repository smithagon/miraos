import subprocess
import shlex

class TerminalService:
    @staticmethod
    def execute(command: str) -> dict:
        try:
            args = shlex.split(command)
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out after 30s", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}
