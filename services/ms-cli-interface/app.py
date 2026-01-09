#!/usr/bin/env python3
"""
CLI Interface for Samantha - Your Personal Assistant
"""
import argparse
import asyncio
import random
import signal
import uuid
from typing import Dict, Any, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.status import Status

# Local imports
from src.nlp_client import NLPClient
from src.config import config

# Initialize console
console = Console()


class SamanthaCLI:
    """Main CLI application for Samantha."""

    def __init__(self, email: Optional[str] = None, access_token: Optional[str] = None):
        self.nlp_client = NLPClient(
            base_url=config.get_nlp_service_url(),
            access_token=access_token
        )
        self.running = True
        self.email = email
        self.history = InMemoryHistory()
        self.key_bindings = self._create_key_bindings()
        self.session = PromptSession(history=self.history, key_bindings=self.key_bindings)
        self.thread_id = self._generate_thread_id()

        # Register signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)
    
    def _handle_interrupt(self, signum, frame):
        """Handle interrupt signals for graceful shutdown."""
        self.running = False
        console.print("\n[red]chat ecerrado[/]")
    
    def display_welcome(self):
        """Display welcome message"""
        console.print(
            Panel.fit(
                "[bold blue]🌟 Bem-vindo ao Samantha! 🌟[/]\n\n"
                "[italic]Seu assistente pessoal inteligente.[/]\n"
                "Digite 'sair' para encerrar o chat.",
                title=f"{config.get_app_name()} v{config.get_app_version()}",
                border_style="blue",
                padding=(1, 2)
            )
        )
    
    async def process_input(self, user_input: str) -> str:
        """Process user input using the NLP service."""
        try:
            with Status("Pensando...", spinner="dots"):
                response = await self.nlp_client.process_text(
                    user_input,
                    self.email,
                    thread_id=self.thread_id
                )
                
                # Check if authentication is required
                if response.get("requires_auth", False):
                    console.print(f"\n[red]⚠️ {response.get('response', 'Erro de autenticação')}[/]")
                    console.print("\nPor favor, faça login novamente para continuar.")
                    console.print("Execute o comando a seguir para obter um novo token:")
                    console.print("  [bold]curl http://localhost:8080/test-token/seu-email@exemplo.com[/]")
                    console.print("E depois execute o cliente com o novo token:")
                    console.print(f"  [bold]python -m app --email seu-email@exemplo.com --token SEU_TOKEN_AQUI[/]\n")
                    self.running = False
                    return ""
                    
                return response.get("response", "Desculpe, não consegui processar sua mensagem.")
                
        except Exception as e:
            console.print(f"\n[red]Erro ao processar mensagem: {e}[/]")
            return "Ocorreu um erro ao processar sua mensagem. Por favor, tente novamente."
    
    async def run(self):
        """Run the CLI application."""
        self.display_welcome()
        console.print(f"[dim]Thread atual: {self.thread_id}[/]")
        
        while self.running:
            try:
                # Get user input with prompt_toolkit session
                user_input = await self.session.prompt_async("\nVocê: ")
                
                # Check for exit command
                if user_input.lower() in ('sair', 'exit', 'quit'):
                    self.running = False
                    console.print("\n[blue]Até logo! Estarei aqui se precisar de mais algo. 😊[/]")
                    break
                
                # Process the input and get response
                response = await self.process_input(user_input)
                
                # Display Samantha's response
                console.print(f"\n[bold magenta]Samantha:[/] {response}")
                
            except KeyboardInterrupt:
                self.running = False
                console.print("\n\n[red]Encerrando o chat...[/]")
                break
            except Exception as e:
                console.print(f"\n[red]Ocorreu um erro: {e}[/]")
                continue
            
    async def close(self):
        """Clean up resources."""
        await self.nlp_client.close()

    def _generate_thread_id(self) -> str:
        """Generate a short unique thread identifier."""
        return uuid.uuid4().hex[:8]

    def _start_new_thread(self):
        """Reset the conversation thread and notify the user."""
        previous_thread = self.thread_id
        self.thread_id = self._generate_thread_id()
        console.print(
            f"\n[cyan]🔁 Nova thread iniciada[/] "
            f"(anterior: {previous_thread} → atual: {self.thread_id})"
        )

    def _create_key_bindings(self) -> KeyBindings:
        """Configure custom key bindings for the CLI session."""
        kb = KeyBindings()

        @kb.add("enter")
        def _(event):
            """
            Shift+Enter: inicia uma nova thread.
            Enter sozinho: envia a mensagem normalmente.
            """
            if self._is_shift_enter_event(event):
                event.app.current_buffer.reset()
                self._start_new_thread()
            else:
                event.app.current_buffer.validate_and_handle()

        return kb

    @staticmethod
    def _is_shift_enter_event(event) -> bool:
        """
        Best-effort detection of Shift+Enter using CSI-u escape codes.
        """
        if not event.key_sequence:
            return False

        last_key = event.key_sequence[-1]
        data = getattr(last_key, "data", "") or ""

        # Check for CSI u format: ESC [ <keycode> ; <modifier> u
        if data.startswith("\x1b[") and data.endswith("u"):
            payload = data[2:-1]
            parts = payload.split(";")

            if len(parts) >= 2 and parts[0] == "13":  # 13 == Enter
                try:
                    modifier = int(parts[1])
                except ValueError:
                    return False

                # Modifier encoding follows xterm: 1 (base) + bitmask
                # Shift flag is the first bit.
                shift_flag = 1  # after subtracting base (1)
                effective = max(modifier - 1, 0)
                return (effective & shift_flag) == shift_flag

        return False

async def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Samantha - Your Personal Assistant")
    parser.add_argument("--email", type=str, help="Email for authentication")
    parser.add_argument("--token", type=str, help="Access token for authentication")
    args = parser.parse_args()

    cli = SamanthaCLI(
        email=args.email,
        access_token=args.token
    )
    try:
        await cli.run()
    finally:
        await cli.close()

if __name__ == "__main__":
    asyncio.run(main())
