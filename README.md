# Dead vs. Alive

Jogo de áudio para o R36S acessível. Zumbis vêm das quatro direções: mire com
o direcional ou o analógico esquerdo, atire ou golpeie com R2 e recarregue com
X. A cada onda você avança uma sala, com ambiente e eco próprios, e troca de
arma. Com um zumbi na mira, um bipe vindo daquela direção indica a distância
(grave e lento longe, agudo e rápido perto), o que permite jogar sem fone.

Feito em Python com a biblioteca do
[r36s-a11y-sdk](https://github.com/gogabs/r36s-a11y-sdk). O design está em
`docs/jogo-zumbis.md` do repositório
[r36s-a11y](https://github.com/gogabs/r36s-a11y).

## Instalar no console

Com o console montado pelo [r36s-a11y](https://github.com/gogabs/r36s-a11y) e
o SDK clonado ao lado deste repositório:

```bash
./instalar.sh
```

O jogo aparece na galeria sozinho.

## Sons

Os sons em `sounds/` vêm da coleção pessoal do autor (principalmente do jogo
Swamp e de ambientes da pasta "sbyw"), importados por `tools/importar_sons.py`.
Eles não são nossos para redistribuir, por isso este repositório é privado.
Os sons provisórios sintetizados saem de `tools/gerar_sons_provisorios.py`.

## Atualização de 13/10/2026

[Gráficos, SDK atual, sete mapas e validação no console](docs/graficos.md).
