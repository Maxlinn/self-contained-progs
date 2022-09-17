from collections import UserDict


class PathDict(UserDict):
    '''
    PathDict will evaluate `dict[key]` where key is path-like (e.g. `key='a/b/c'`)
        thus avoiding explicit consecutive indexing.
        e.g. dict: d['a']['b']['c'] = 1 -> {'a': {'b': {'c': 1} } }
            PathDict: d['a/b/c'] = 1 -> {'a': {'b': {'c': 1} } }

    Implementation:
        *Fluent Python* suggests that, if user wants to implement a custom dict class,
        it should inherit from `collection.UserDict`, not plain `dict`.

        In `collection.UserDict`, the actual key-value storage is based on its `self.data :dict` member,
        other methods are just encapsulations of `self.data`, nothing surprising.
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getitem__(self, item: str):
        # `it` stands for `iterator`
        it = self.data
        # `str.split()` will at least return one element, `''.split() -> ['']`
        segments = item.split('/')
        for seg in segments:
            if not isinstance(it, dict):
                raise KeyError(f"stem '{seg}' of '{item}' already has a non-mapping object.")

            if seg not in it.keys():
                raise KeyError(f"stem '{seg}' of '{item}' does not exist.")
            # if seg is stem, then it goes deeper mapping
            # if seg is leaf, then it retrieves final value
            it = it[seg]
        return it

    def __setitem__(self, key: str, value):
        it = self.data
        segments = key.split('/')
        for i, seg in enumerate(segments):
            # judging if seg is stem
            if i < (len(segments) - 1):
                if not isinstance(it, dict):
                    raise KeyError(f"stem '{seg}' of '{key}' already has a non-mapping object.")
                # if stem does not exist yet, create one
                if seg not in it.keys():
                    it[seg] = {}
                it = it[seg]
            else:
                it[seg] = value


if __name__ == '__main__':
    # test case of https://bbs.byr.cn/#!article/Python/26174
    d = PathDict({'a': {'b': 1, 'c': 2}})
    print(d)
    print(d['a/b'])
    d['e/f/g'] = 2
    print(d)
