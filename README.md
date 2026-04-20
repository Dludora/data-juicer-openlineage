# data-juicer-openlineage

OpenLineage metadata provider plugin for [py-data-juicer](https://github.com/datajuicer/data-juicer).

## Install

```bash
pip install py-data-juicer
pip install data-juicer-openlineage
```

For local development against a checkout of `py-data-juicer`:

```bash
pip install -e /Users/dludora/Code/data-juicer
pip install -e /Users/dludora/Code/data-juicer-openlineage
```

## Configure

```yaml
metadata:
  enabled: true
  providers:
    - name: openlineage
      enabled: true
      config:
        transport:
          type: http
          url: http://localhost:5000
          endpoint: api/v1/lineage
```

HTTP shortcut config is also supported:

```yaml
metadata:
  providers:
    - name: openlineage
      enabled: true
      config:
        transport_type: http
        url: http://localhost:5000
        endpoint: api/v1/lineage
        api_key: secret
        timeout: 5
        retry_count: 2
        retry_backoff_seconds: 0.5
```

## Notes

- The plugin depends on `py-data-juicer` runtime metadata objects such as `Ctx` and `OpCtx`.
- Custom facet schema URLs default to the `Dludora/data-juicer-openlineage` raw GitHub path. Override with `DATA_JUICER_OPENLINEAGE_SCHEMA_BASE_URL` if you publish the package under a different repository.
