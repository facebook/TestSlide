# TestSlide Snippets collection

Set of snippets to help and conveniently sepeed up the writing of tests using [TestSlide](https://testslide.readthedocs.io).

## Features

The snippets follow some common guidelines:

- All snippets are prefixed with `ts` (for TestSlide).

## Requirements

None, just open a python file, and start writing tests!
You might need to add [TestSlide](https://testslide.readthedocs.io) to your project dependencies though.

## Development

To locally build the extension, with the repository cloned locally, cd into the extension directory (where this README resides), install `vsce`:

* For a global installation:
```
npm -g install vsce
```
* For a local installation:
```
npm install vsce
```

Then run:
```
# If you installed it globally it will already be in the path:
vsce package

# If you installed it locally, it would have generated an nmp_modules directory
# with the binary in it
./node_modules/.bin/vsce package
```

That will generate a `vsix` file, that's the extension that you can then install into vscode (open the omnibar, Shift+Ctrl+P, then write vsix to find "Install from VSIX" option).
Enjoy!

## Release Notes

### Version 2.7.0

Initial release of the snippets.
