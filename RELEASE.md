- Create a new release tag by running:
	- `./release.sh $new_version`
- https://travis-ci.com/facebookincubator/TestSlide/
	- Check if master build is OK.
- https://readthedocs.org/projects/testslide/
	- Trigger bulid for
		- new version
		- master
	- Admin > Versions: make new version the default
- Build & publish
	- `make twine`

- After the above (should have changed the version on package.json), publish a
  new version of testslide-snippets VSCode extension
	- You'll have to be logged in to the publisher `vsce login testslide-snippets`
	- run: `vsce publish`
