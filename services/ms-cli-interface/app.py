#!/usr/bin/env python3
"""
CLI Interface for Samantha - Your Personal Assistant
"""
import asyncio
import random
import signal
from typing import Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import print
from rich.status import Status

# Local imports
from src.nlp_client import NLPClient
from src.config import config

# Initialize console
console = Console()

class SamanthaCLI:
    """Main CLI application for Samantha."""
    
    def __init__(self):
        self.nlp_client = NLPClient(config.get_nlp_service_url())
        self.running = True
        
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
                response = await self.nlp_client.process_text(user_input)
                return response.get("response", "Desculpe, não consegui processar sua mensagem.")
        except Exception as e:
            console.print(f"\n[red]Erro ao processar mensagem: {e}[/]")
            return "Ocorreu um erro ao processar sua mensagem. Por favor, tente novamente."
    
    async def run(self):
        """Run the CLI application."""
        self.display_welcome()
        
        while self.running:
            try:
                # Get user input with rich prompt
                user_input = Prompt.ask("\n[bold]Você[/]")
                
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

async def main():
    """Main entry point for the application."""
    app = SamanthaCLI()
    try:
        await app.run()
    finally:
        await app.close()

if __name__ == "__main__":
    asyncio.run(main())
