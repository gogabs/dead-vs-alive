# Dead vs. Alive: gráficos e SDK atual

Instalado no R36S conectado em 13/10/2026. Os gráficos usam a SDK Python
`76bb5a8d4fbf3b329355c27cbbae320c15494195`, última main consultada pelo GitHub
CLI, com streaming, leituras parciais de evdev, supressão FN, reconexão e
atualização da voz da instalação reconciliados. Não foi mantida a abordagem
intermediária de copiar um módulo gráfico privado: o jogo usa
`r36s_a11y.graphics.Graphics` da SDK nova.

Sete ambientes acompanham a ordem original das ondas: quarto de hospital,
corredor, estacionamento, cozinha, metrô, igreja e floresta. Cenários,
personagem de saia/rabo de cavalo e armas são monocromáticos. Zumbis são
verdes; sangue continua vermelho. As sete armas têm sprites e efeitos próprios.
Morte deixa explosão de 0,5 s e mancha temporária de oito segundos.

O renderer desenha por texturas, sem Pillow no console. Lê SCREEN e ENERGY
sem gravar preferências: desligar Gráficos libera SDL e mantém o áudio;
reativar abre novamente. Atualização lógica permanece a original, enquanto
o desenho usa teto de 30 fps, 20 em economia moderada e 10 em agressiva.
Eventos limitados a 128 capturam impactos/mortes antes da remoção do alvo,
não mudam dano, munição ou aleatoriedade do jogo. Pausa congela os efeitos,
troca de sala limpa o cenário e saída destrói texturas/SDL.

`build.py` monta a camada sobre a referência limpa do jogo e o backup da SDK
instalada em `outputs/dva-integration-2026-10-13/baseline`. A exportação dos
sprites fica em `graphics-preview/build_preview.py`; a galeria atual de mapas
e animações está em `outputs/dva-integration-2026-10-13/art/index.html`.
O pacote não substitui sons ou recordes.

Passaram seis testes locais, incluindo comparação de estado, timers, sons e
estado aleatório das sete armas contra o jogo original. A prova nativa com
perfil privado verificou sete mapas e sete armas, áudio/OpenAL/fala, pausa,
retomada, liberação de vídeo em modo áudio e encerramento. A amostra final
mediu 28,93 fps, mediana de desenho 12,49 ms e máximo 111,45 ms. Máximo inclui
carregamento e capturas; não é latência de controles nem teste prolongado.
Não houve campanha humana ou avaliação auditiva dos novos gráficos.

A primeira prova omitiu ALSOFT_CONF e emitiu avisos de mmap do ALSA. Foi
repetida usando o perfil real da galeria (`mmap=false`), sem esses avisos.
Esse perfil e todos os hashes das preferências permaneceram intactos.

Relatórios/capturas finais locais: `outputs/dva-integration-2026-10-13/`.
No aparelho: `/roms/a11y/updates/dva-native-production-env-20261013/`.
Backup conjunto da SDK, jogo e plataforma:
`/roms/a11y/updates/dva-sdk-pr5-20261013/before.tar.gz`.
Recuperação: `sudo sh /roms/a11y/updates/dva-sdk-pr5-20261013/rollback.sh`.
O timer de recuperação foi cancelado após as verificações.

A plataforma também recebeu os quatro pedidos principais do revisor do PR5,
incluindo o PR4 Data e hora/Salvar/Cancelar. Passaram 40 testes no PC e no
console e 99 telas nativas nos três tamanhos. Os 81 arquivos do recibo
conjunto devem corresponder aos hashes instalados; `receipt.json` guarda
também os hashes de sistema/voz/áudio preservados.

## Capturas reais e desenvolvimento neste repositório

![Hospital no R36S](imagens/map-hospital_quarto.png)

![Floresta no R36S](imagens/map-floresta.png)

Para conferir as regras sem hardware: `python3 -m unittest discover -s tests`.
Para exportar prévias editáveis: `python3 tools/pixelart/build_preview.py --output previews` (Pillow somente no PC).
Os caminhos build.py/baseline mencionados acima documentam o workspace da instalação; neste repositório os assets e a SDK reconciliada já estão incluídos e `instalar.sh` usa essa cópia.
