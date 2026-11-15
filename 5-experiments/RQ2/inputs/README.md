# Insumos da RQ2

Cópias dos arquivos de que a bateria depende, guardadas para o pacote de replicação. Os scripts não leem estas cópias: `run_rq2.py` usa o Retriever de produção, que lê `3-dejavu/configs/`. O teste `test_input_snapshot_is_what_the_production_retriever_reads` confere que as cópias são iguais ao que o Retriever carregou.

## `dejavu_configs/`

Catálogo e pesos usados na bateria, copiados de `3-dejavu/configs/` em 2026-11-10.

| Arquivo | Origem | SHA-256 |
|---|---|---|
| `scenario_catalogue.json` | `3-dejavu/configs/arm/scenario_catalogue.json` | `c3122aaba8db2e66fd3808f28f7072e2e1e801273df7519af4a52ad0ecb20f8c` |
| `weights_config.yaml` | `3-dejavu/configs/weights_config.yaml` | `e4325c8048efdaa5c06782c4a4169c59d58576d545efdafa76558a4a04c55720` |

O run de origem de D0 copiou esses dois arquivos com outra formatação (JSON reindentado, quebras de linha CRLF), mas com o mesmo conteúdo: os objetos carregados são iguais.

## `d0_source/`

Origem de D0: o run `15_0_140` da sequência principal da RQ1.2 (atrito lateral 0,140). A pasta `results/` da RQ1.2 não é versionada; estes arquivos são cópias exatas dela.

| Arquivo | Conteúdo | SHA-256 |
|---|---|---|
| `experiment.json` | Configuração do run (`lateral_friction = 0.14`) | `1b99efc1b1ca5b64b954a2a01218ed4f0bb0f4f068f400d46bf605e09ffc96b5` |
| `events_20261108_172059.jsonl` | Eventos do pipeline. O evento `diagnosis` (episódio 1, passo 23, `LIFT_OBJECT`) é D0, e o evento `ranking` é o ranking gravado em `diagnoses.json` | `6adb1fae488309e0f6fe109dd6bdaf22edd24aec9f389037ec4b25aca2a8fbba` |
| `outcome.json` | Resultado do run: C1 em primeiro lugar, sucesso na primeira tentativa e objetivo global atingido | `d7e787dd1da7b41f9b6e5db8e95b239406198c2ed90a50a313545a0312276b45` |

O teste `test_reference_is_the_diagnosis_recorded_in_rq1_2` lê D0 desta cópia e, quando a pasta original existe, confere que a cópia é idêntica.
