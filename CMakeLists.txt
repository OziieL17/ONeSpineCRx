cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)
project(ONeSpineCRx)
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})
set(EXTENSION_HOMEPAGE "https://github.com/OziieL17/ONeSpineCRx")
set(EXTENSION_CATEGORY "ONe")
set(EXTENSION_CONTRIBUTORS "Alexis Oziel Martinez Nava")
set(EXTENSION_DESCRIPTION "Guided 2D cervical radiographic geometry, measurements and dynamic analysis")
set(EXTENSION_ICONURL "")
set(EXTENSION_SCREENSHOTURLS "")
set(EXTENSION_DEPENDS "NA")
set(MODULE_PYTHON_SCRIPTS
  ${PROJECT_NAME}.py
  ONeSpineCRxLib/__init__.py
  ONeSpineCRxLib/engine.py
  ONeSpineCRxLib/report.py
)
slicerMacroBuildScriptedModule(NAME ${PROJECT_NAME} SCRIPTS ${MODULE_PYTHON_SCRIPTS})
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
