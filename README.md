# self-contained-progs
Collections of scattered programs, either one-file or one-dir, but all self-contained.

## save_manager.py

save manager deals with your save files when slots in games are limited, with external save files storage and cmd-line interface to swap in and out save file with game.

## pathdict.py

implemeted a `PathDict` mapping class.

```markdown
PathDict will evaluate `dict[key]` where key is path-like (e.g. `key='a/b/c'`)
        thus avoiding explicit consecutive indexing.
        e.g. dict: d['a']['b']['c'] = 1 -> {'a': {'b': {'c': 1} } }
            PathDict: d['a/b/c'] = 1 -> {'a': {'b': {'c': 1} } }
```

