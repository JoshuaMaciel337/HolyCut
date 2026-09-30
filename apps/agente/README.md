# Agente de envio do OBS

Programa pequeno que roda no computador da mídia. Quando o culto termina e o OBS para de gravar, ele envia a gravação sozinho para o HolyCut. Ninguém precisa abrir o site nem esperar o upload.

## Como funciona

- Olha a pasta onde o OBS salva as gravações a cada 30 segundos.
- Considera que a gravação terminou quando o arquivo fica 2 minutos sem mudar de tamanho.
- Envia em pedaços de 8 MB. Se a internet cair, continua de onde parou na próxima volta, sem mandar tudo de novo.
- Se o OBS grava em MKV e converte para MP4, envia só o MP4.
- Na primeira vez, as gravações que já estavam na pasta só são marcadas como vistas. Ele envia as novas, a partir daí.

## Instalar (uma vez)

1. Instale o Python 3.11 ou mais novo, em https://www.python.org/downloads/. Na instalação, marque **"Add python.exe to PATH"**.
2. No HolyCut, abra **Envio automático**, crie uma chave (por exemplo, "PC da mídia") e copie. Ela só aparece uma vez.
3. Copie esta pasta (`agente`) para o computador da mídia.
4. Dê dois cliques em `iniciar_agente.bat`. Na primeira vez, ele pergunta:
   - o endereço do HolyCut;
   - a chave de envio;
   - a pasta onde o OBS salva as gravações (no OBS: Configurações > Saída > Caminho da gravação).

As respostas ficam salvas. Da próxima vez, ele já começa sozinho.

## Iniciar junto com o Windows

1. Aperte `Win + R`, digite `shell:startup` e dê Enter.
2. Nessa pasta, crie um atalho para `iniciar_agente.bat`.
3. Nas propriedades do atalho, no fim do campo **Destino**, acrescente ` --automatico`. Em **Executar**, escolha **Minimizada**.

## Opções

| Opção | O que faz |
|---|---|
| `--agora` | Confere a pasta uma vez e fecha |
| `--automatico` | Fica rodando sem fazer perguntas |
| `--enviar-existentes` | Na primeira vez, envia também as gravações que já estavam na pasta |
| `--minutos-estavel 5` | Espera 5 minutos sem mudança antes de enviar (o padrão é 2) |
| `--pasta`, `--servidor`, `--chave` | Trocam a configuração salva |

A configuração, a lista do que já foi enviado e o registro do que aconteceu (`agente.log`) ficam em `C:\Users\<você>\.holycut\`.

## Se algo der errado

- **"A chave de envio foi recusada"**: a chave foi revogada no site. Crie outra e rode com `--chave nova-chave`.
- **"Sem conexão"**: o agente tenta de novo sozinho na próxima volta. O que já foi enviado não se perde.
- **"O servidor está sem espaço"**: avise quem cuida do HolyCut. O agente continua tentando.
