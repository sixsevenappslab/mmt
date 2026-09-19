# Esquema canónico MMM-ready / Canonical MMM-ready schema

Una tabla MMM-ready es larga: una fila representa una combinación de fecha, zona geográfica y
canal. El CSV lleva siempre un sidecar `nombre.meta.json`.

| Columna | Tipo / unidad | Regla |
| --- | --- | --- |
| `date` | fecha `YYYY-MM-DD` | Parte de la clave primaria. |
| `geo` | texto | Parte de la clave; usar `national` para una serie nacional. |
| `channel` | identificador `^[a-z][a-z0-9_]*$` | Parte de la clave. |
| `spend` | número EUR u otra moneda indicada | No negativo. |
| `impressions` | número | Opcional, anulable, no negativo. |
| `clicks` | número | Opcional, anulable, no negativo. |
| `kpi` | número | Debe ser idéntico para todos los canales de la misma fecha y geo. |
| `control_*` | número | Cada control debe ser idéntico para todos los canales de la misma fecha y geo. |

La clave primaria es `date`, `geo`, `channel`. Nunca se infiere la moneda, la granularidad ni
la zona horaria desde una fecha o un valor de gasto.

## Metadatos / Metadata

El archivo `nombre.meta.json` debe incluir:

```json
{
  "schema_version": "1.0",
  "currency": "EUR",
  "granularity": "weekly-mon",
  "timezone": "Europe/Madrid",
  "geos": ["national"],
  "channels": ["search", "social"]
}
```

`currency` is an ISO-4217 three-letter code. `granularity` is one of `daily`, `weekly-mon`,
or `weekly-sun`; `timezone` is an IANA timezone. When optional `geos` or `channels` are
present, they must agree with the CSV.

## English

The canonical table is long: one row per date, geography, and media channel. `date`, `geo`,
`channel`, `spend`, and `kpi` are required; `impressions` and `clicks` are optional nullable
media fields. The primary key is `(date, geo, channel)`, while KPI and every `control_*` field
must remain invariant within a date and geo. The adjacent metadata sidecar makes currency,
time granularity, and timezone explicit rather than guessed.

## Conversion targets

Both targets share the same wide layout: one row per `time` (the `date` formatted
`YYYY-MM-DD`), the `kpi`, every `control_*` column, and one `spend_<channel>` column per
channel.

`convert.py --to meridian` additionally emits `impressions_<channel>` when the long table has
non-null impressions, and keeps `geo` only for multi-geo data. This is the wide CSV used to
populate Meridian's `DataFrameInputDataBuilder` (`default_time_column="time"`,
`media_spend_cols=spend_*`, `media_cols=impressions_*`). Meridian also needs a population per
geo to fit a multi-geo model; that dimension is not part of this media schema and is never
invented.

`convert.py --to pymc` emits the national wide shape without `geo` and without impressions
(`date_column="time"`, `channel_columns=spend_*`). It rejects multiple geographies because
PyMC-Marketing needs model `dims` for that, which this repository does not define yet.
