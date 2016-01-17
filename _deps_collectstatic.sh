#!/bin/sh
set -e
set -x

mkdir -p dockci/static/lib/css
mkdir -p dockci/static/lib/fonts
mkdir -p dockci/static/lib/js

cp bower_components/bootstrap/dist/css/bootstrap.min.css dockci/static/lib/css

cp bower_components/bootstrap/dist/fonts/glyphicons-halflings-regular.woff dockci/static/lib/fonts
cp bower_components/bootstrap/dist/fonts/glyphicons-halflings-regular.ttf dockci/static/lib/fonts

cp bower_components/ansi_up/ansi_up.js dockci/static/lib/js
cp bower_components/blueimp-md5/js/md5.min.js dockci/static/lib/js/md5.js
cp bower_components/bootstrap/dist/js/bootstrap.min.js dockci/static/lib/js/bootstrap.js
cp bower_components/bootstrap-material-design/dist/js/material.min.js dockci/static/lib/js/material.js
cp bower_components/bootstrap-material-design/dist/js/ripples.min.js dockci/static/lib/js/ripples.js
cp bower_components/jquery/dist/jquery.min.js dockci/static/lib/js/jquery.js
cp bower_components/knockout/dist/knockout.js dockci/static/lib/js
cp bower_components/knockstrap/build/knockstrap.min.js dockci/static/lib/js/knockstrap.js
cp bower_components/requirejs/require.js dockci/static/lib/js
cp bower_components/requirejs-text/text.js dockci/static/lib/js
cp bower_components/uri.js/src/jquery.URI.min.js dockci/static/lib/js/jquery.URI.js
cp bower_components/uri.js/src/URI.min.js dockci/static/lib/js/URI.js
cp bower_components/stomp.js/lib/stomp.js dockci/static/lib/js/stomp.js
