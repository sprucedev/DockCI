#!/bin/sh -x
ls -la bower_components/
ls -la bower_components/bootstrap/
ls -la bower_components/bootstrap/dist/
ls -la bower_components/bootstrap/dist/css/
cp bower_components/bootstrap/dist/css/bootstrap.min.css dockci/static/lib/css
cp bower_components/bootstrap-material-design/dist/css/material.min.css dockci/static/lib/css
cp bower_components/bootstrap-material-design/dist/css/material-wfont.min.css dockci/static/lib/css
cp bower_components/bootstrap-material-design/dist/css/ripples.min.css dockci/static/lib/css

cp bower_components/bootstrap-material-design/dist/fonts/Material-Design-Icons.woff dockci/static/lib/fonts
cp bower_components/bootstrap-material-design/dist/fonts/Material-Design-Icons.ttf dockci/static/lib/fonts

cp bower_components/ansi_up/ansi_up.js dockci/static/lib/js
cp bower_components/blueimp-md5/js/md5.min.js dockci/static/lib/js
cp bower_components/bootstrap/js/dropdown.js dockci/static/lib/js
cp bower_components/bootstrap/js/modal.js dockci/static/lib/js
cp bower_components/bootstrap/js/tab.js dockci/static/lib/js
cp bower_components/bootstrap/js/transition.js dockci/static/lib/js
cp bower_components/bootstrap-material-design/dist/js/material.min.js dockci/static/lib/js
cp bower_components/bootstrap-material-design/dist/js/ripples.min.js dockci/static/lib/js
cp bower_components/jquery/dist/jquery.min.js dockci/static/lib/js
cp bower_components/uri.js/src/jquery.URI.min.js dockci/static/lib/js
cp bower_components/uri.js/src/URI.min.js dockci/static/lib/js
