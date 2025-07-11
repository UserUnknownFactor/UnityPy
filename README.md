# UnityPy

A Unity asset extractor for Python based on [AssetStudio](https://github.com/Perfare/AssetStudio).

Next to extraction it also supports editing Unity assets.
So far following obj types can be edited:
  - Texture2D
  - Sprite(indirectly via linked Texture2D)
  - TextAsset
  - MonoBehaviour

## Installation

**Python 3.10.0 or higher is required**

Download/clone the git and use:

```cmd
pip install .
```

### Usage

Take a look at [/examples/dump_assets.py](/examples/dump_assets.py) for an example of usage.

This fork can also dump scene trees of GameObjects and their descendants showing their names and IDs in the file.

