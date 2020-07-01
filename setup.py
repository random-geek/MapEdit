import setuptools
import mapedit


def get_long_desc():
	with open("README.md", "r") as f:
		return f.read()


setuptools.setup(
	name="mapedit",
	version=mapedit.__version__,
	description=mapedit.__doc__.strip(),
	long_description=get_long_desc(),
	long_description_content_type="text/markdown",
	author=mapedit.__author__,
	url="https://github.com/random-geek/MapEdit",
	license=mapedit.__license__,

	packages=setuptools.find_packages(),
	entry_points={
		"console_scripts": [
			"mapedit = mapedit.cmdline:run_cmdline"
		]
	},
	python_requires=">=3.8",
	install_requires="numpy"
)
