# ArchPython CLI

CLI para geração de serviços em arquitetura limpa.

## Instalação

```bash
pip install archpython-cli
```

## Uso

### Criar um novo módulo

```bash
archpython m nome_do_modulo
```

### Criar um novo serviço

```bash
archpython s
```

O comando irá guiar você através de um processo interativo para criar um novo serviço, onde você poderá:
1. Escolher o tipo de serviço (domain, application, infra, shared)
2. Definir o nome do serviço
3. Escolher o módulo (exceto para serviços shared)
4. Decidir se deseja criar DTOs automaticamente

## Estrutura do Projeto

O CLI gera uma estrutura de arquivos seguindo os princípios da arquitetura limpa:

```
src/
  modules/
    seu_modulo/
      services/
        domain/
        application/
        infra/
      dtos/
    shared/
      services/
        seu_servico/
          dtos/
```

## Requisitos

- Python >= 3.12
