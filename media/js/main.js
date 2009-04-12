// Copyright The Android Open Source Project
// All Rights Reserved.

/**
 * @fileoverview Power Droid main page support.
 *
 * NOTE(dart) This library only supports firefox/mozilla.
 *
 * MochiKit is used here. <http://www.mochikit.com/> 
 *
 * @author dart@google.com (Keith Dart)
 */



function showExtraMessage(msg) {
  placeContent("extra", P(msg));
};

function hideExtraMessage() {
  placeContent("extra", null);
};


/**
 * Main applet.
 */
function MainApp() {
//  this.measureifc = new PythonProxy("/droid/json/measure/");
};

MainApp.prototype.destroy = function() {
  placeContent("extra", null);
};

