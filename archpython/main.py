from pathlib import Path
import typer
from typing import List, Tuple
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table

app = typer.Typer()
console = Console()


@dataclass
class ServiceConfig:
    name: str
    module: str
    type: str
    create_dtos: bool


class ModuleManager:
    def __init__(self, base_path: Path = Path("src/modules")):
        self.base_path = base_path

    def get_available_modules(self) -> List[str]:
        if not self.base_path.exists():
            raise FileNotFoundError("❌ Diretório src/modules não encontrado")

        # Filtrar o módulo 'shared' da lista de módulos disponíveis
        modules = [
            d.name
            for d in self.base_path.iterdir()
            if d.is_dir() and d.name != "shared"
        ]
        if not modules:
            raise FileNotFoundError("❌ Nenhum módulo encontrado em src/modules")

        return modules

    def get_module_path(self, module_name: str) -> Path:
        return self.base_path / module_name


class DTOGenerator:
    def __init__(self, module_path: Path, service_name: str, service_type: str):
        self.module_path = module_path
        self.service_name = service_name.lower()  # Garantir snake case
        self.service_type = service_type

        # Definir o diretório dos DTOs baseado no tipo de serviço
        if service_type == "shared":
            # Para shared, DTOs ficam na mesma pasta do service
            self.dtos_dir = module_path / "services" / self.service_name / "dtos"
        else:
            # Para outros tipos, mantém a estrutura anterior
            self.dtos_dir = module_path / "dtos" / service_name

        self.request_class_name = "".join(
            word.capitalize() for word in f"{service_name}_request_dto".split("_")
        )
        self.response_class_name = "".join(
            word.capitalize() for word in f"{service_name}_response_dto".split("_")
        )

    def generate(self) -> Tuple[str, str]:
        self.dtos_dir.mkdir(parents=True, exist_ok=True)

        # Criar arquivos DTO
        request_file = self.dtos_dir / f"{self.service_name}_request_dto.py"
        response_file = self.dtos_dir / f"{self.service_name}_response_dto.py"

        if request_file.exists() or response_file.exists():
            raise FileExistsError(f"❌ Já existem DTOs para {self.service_name}")

        request_file.write_text(f"class {self.request_class_name}:\n    pass\n")
        response_file.write_text(f"class {self.response_class_name}:\n    pass\n")

        # Criar __init__.py
        init_content = f"""from .{self.service_name}_request_dto import {self.request_class_name}
from .{self.service_name}_response_dto import {self.response_class_name}

__all__ = ['{self.request_class_name}', '{self.response_class_name}']
"""
        (self.dtos_dir / "__init__.py").write_text(init_content)

        return self.request_class_name, self.response_class_name


class ServiceGenerator:
    def __init__(self, module_path: Path, config: ServiceConfig):
        self.module_path = module_path
        self.config = config
        self.service_name = config.name.lower()  # Garantir snake case

        if config.type == "shared":
            # Para shared, criar pasta com nome do service
            self.service_dir = module_path / "services" / self.service_name
        else:
            # Para outros tipos, manter estrutura anterior
            self.service_dir = module_path / "services" / config.type

        self.service_class_name = (
            "".join(word.capitalize() for word in config.name.split("_")) + "Service"
        )
        self.adapter_class_name = (
            "".join(word.capitalize() for word in config.type.split("_")) + "Service"
        )

        # Configurar ambiente Jinja2
        template_dir = Path(__file__).parent / "template"
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def _get_template_content(
        self, request_class: str = "", response_class: str = ""
    ) -> str:
        template = self.env.get_template(f"{self.config.type}_service.j2")

        # Renderizar template com os dados
        content = template.render(
            service_name=self.service_class_name.replace("Service", ""),
            request_dto=request_class if request_class else "None",
            response_dto=response_class if response_class else "None",
        )

        return content

    def generate(self, request_class: str = "", response_class: str = "") -> None:
        self.service_dir.mkdir(parents=True, exist_ok=True)
        service_file = self.service_dir / f"{self.service_name}_service.py"

        if service_file.exists():
            raise FileExistsError(
                f"❌ Já existe um service {self.service_name}_service.py"
            )

        # Gerar conteúdo do service usando o template
        service_content = self._get_template_content(request_class, response_class)

        # Adicionar imports dos DTOs se necessário
        if self.config.create_dtos:
            if self.config.type == "shared":
                service_content = (
                    f"from src.modules.{self.config.module}.services.{self.service_name}.dtos import {request_class}, {response_class}\n\n"
                    + service_content
                )
            else:
                service_content = (
                    f"from src.modules.{self.config.module}.dtos.{self.service_name} import {request_class}, {response_class}\n\n"
                    + service_content
                )

        service_file.write_text(service_content)


def get_service_config() -> ServiceConfig:
    # Selecionar tipo de serviço primeiro
    service_types = ["domain", "application", "infra", "shared"]
    
    # Criar tabela para tipos de serviço
    table = Table(title="Tipos de Serviço Disponíveis", show_header=True, header_style="bold magenta")
    table.add_column("Número", style="cyan")
    table.add_column("Tipo", style="green")
    
    for i, service_type in enumerate(service_types, 1):
        table.add_row(str(i), service_type)
    
    console.print(Panel(table, title="[bold blue]Selecione o Tipo de Serviço[/bold blue]"))
    
    type_index = int(Prompt.ask(
        "Digite o número do tipo de serviço",
        default="1"
    )) - 1
    
    if type_index < 0 or type_index >= len(service_types):
        raise ValueError("❌ Tipo de serviço inválido")
    
    selected_type = service_types[type_index]
    
    # Perguntar nome do serviço
    service_name = Prompt.ask(
        "[bold blue]Digite o nome do serviço[/bold blue]",
        console=console
    )
    
    # Se for shared, não precisa selecionar módulo
    if selected_type == "shared":
        create_dtos = Prompt.ask(
            "[bold blue]Deseja criar os DTOs automaticamente?[/bold blue]",
            choices=["s", "n"],
            default="s",
            show_choices=True,
            console=console
        ) == "s"
        
        return ServiceConfig(
            name=service_name,
            module="shared",
            type=selected_type,
            create_dtos=create_dtos,
        )
    
    # Para outros tipos, selecionar módulo
    module_manager = ModuleManager()
    available_modules = module_manager.get_available_modules()
    
    # Criar tabela para módulos
    table = Table(title="Módulos Disponíveis", show_header=True, header_style="bold magenta")
    table.add_column("Número", style="cyan")
    table.add_column("Módulo", style="green")
    
    for i, module in enumerate(available_modules, 1):
        table.add_row(str(i), module)
    
    console.print(Panel(table, title="[bold blue]Selecione o Módulo[/bold blue]"))
    
    module_index = int(Prompt.ask(
        "Digite o número do módulo",
        default="1",
        console=console
    )) - 1
    
    if module_index < 0 or module_index >= len(available_modules):
        raise ValueError("❌ Módulo inválido")
    
    create_dtos = Prompt.ask(
        "[bold blue]Deseja criar os DTOs automaticamente?[/bold blue]",
        choices=["s", "n"],
        default="s",
        show_choices=True,
        console=console
    ) == "s"
    
    return ServiceConfig(
        name=service_name,
        module=available_modules[module_index],
        type=selected_type,
        create_dtos=create_dtos,
    )


@app.command("m")
def generate_module(name: str):
    module_path = Path("src/modules/" + name)
    module_path.mkdir(parents=True, exist_ok=True)
    console.print("[bold green]✅ Módulo criado com sucesso![/bold green]")


@app.command("s")
def generate_service():
    try:
        config = get_service_config()
        module_manager = ModuleManager()
        module_path = module_manager.get_module_path(config.module)
        
        request_class = ""
        response_class = ""
        
        if config.create_dtos:
            dto_generator = DTOGenerator(module_path, config.name, config.type)
            request_class, response_class = dto_generator.generate()
            console.print(f"[bold green]✅ DTOs criados em {dto_generator.dtos_dir}[/bold green]")
        
        service_generator = ServiceGenerator(module_path, config)
        service_generator.generate(request_class, response_class)
        console.print(
            f"[bold green]✅ Service criado em {service_generator.service_dir / f'{service_generator.service_name}_service.py'}[/bold green]"
        )
        
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        console.print(f"[bold red]{str(e)}[/bold red]")
        return


if __name__ == "__main__":
    app()
