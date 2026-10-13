# Origem e atualização da SDK

A cópia de reserva em `r36s_a11y/` corresponde à main de
[gogabs/r36s-a11y-sdk](https://github.com/gogabs/r36s-a11y-sdk) no commit
`3f12376e3548f1880dda5f6f9937ea630c8e8e6c`, que inclui o PR3 de compatibilidade.
Não há patches exclusivos do jogo sobre essa versão. `sdk-origin.json`
registra os hashes dos arquivos copiados.

O instalador prefere um clone da SDK quando disponível, inclusive um caminho
fornecido explicitamente. A cópia incluída é uma reserva para instalação sem
clone; não recebe alterações futuras automaticamente. Para atualizar o clone:

```sh
git -C ../r36s-a11y-sdk pull --ff-only
./instalar.sh r36s ../r36s-a11y-sdk
```

Para atualizar também a cópia de reserva antes de publicar uma nova versão:

```sh
python3 tools/sync_sdk.py --sdk ../r36s-a11y-sdk
python3 -m unittest discover -s tests
git diff -- r36s_a11y sdk-origin.json
```

O sincronizador exige um checkout limpo, copia os arquivos da SDK sem caches,
retira fontes Python obsoletas dentro da reserva e registra o commit exato.
Revise e publique os arquivos e metadados juntos. O script não atualiza o
clone da SDK nem instala algo no console.
