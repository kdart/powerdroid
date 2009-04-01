/* main */

function loadMeasureApp() {
  loadApp(MeasureApp);
};


function MeasurementTable() {
  var measuretable = TABLE({id: "measuretable"});
  measuretable.appendChild(createDOM("caption", null, "Measurements"));
  measuretable.appendChild(createDOM("thead", {id: "measuretablehead"}));
  measuretable.appendChild(createDOM("tbody", {id: "measuretablebody"}));
  this._table = measuretable;
};

MeasurementTable.prototype.AddHeadings = function(headings) {
  placeContent("measuretablehead", headDisplay(headings));
};

MeasurementTable.prototype.AddRow = function(row) {
  appendContent("measuretablebody", rowDisplay(row));
};


/**
 * Measurement applet.
 */
function MeasureApp() {
  this.measureifc = new PythonProxy("/droid/json/measure/");
  this.root = DIV({id: "inspectorapp", "class": "applet"});
  var buttonbar = DIV({id: "buttonbar", class: "buttonbar"});
  var img = IMG({id: "chart", width: "640", height: "300"});
  this.root.appendChild(buttonbar);
  this.root.appendChild(img);
  // major sections.
  var frm = FORM({method: "post", action: "."});
  frm.appendChild(LABEL({"for": "deviceid"}, "Power Supply:"));
  frm.appendChild(INPUT({name: "deviceid", type: "text", value: "powersupply"}));
  frm.appendChild(LABEL({"for": "voltagle"}, "Voltage:"));
  frm.appendChild(INPUT({name: "voltage", type: "text", value: "3.7"}));
  frm.appendChild(INPUT({name: "measurego", type: "submit", value: "Measure"}));
  this._frmhandle = connect(frm, "onsubmit", bind(this._measureSubmitHandler, this));
  placeContent("extra", frm);
//  deviceid = "powersupply"
//  mode = "N"
//  N = 500
//  samples = 2048
//  delay = 0.5
//  interval = 15.6e-6
//  voltage = 3.7
//  filename = None
//  format = "T"
//  reset = False
//  clear = False
};

MeasureApp.prototype.destroy = function() {
  disconnect(this._frmhandle);
  placeContent("extra", null);
};

MeasureApp.prototype._measureSubmitHandler = function(ev) {
  ev.stop();
  var frm = ev.src();
  var contents = formContents(frm);
  var deviceid = contents[1][0]; // first value, the powersupply field.
  var d = this.measureifc.MeasureCurrent(deviceid);
  d.addCallback(bind(this._receiveMeasure, this));
  return false;
};

MeasureApp.prototype._receiveMeasure = function(value) {
  placeContent("footer", P(null, "Measured current: " + value)); // XXX
};


/**
 * Chart applet.
 */

function loadChartDisplayApp() {
  loadApp(ChartDisplayApp);
};


function ChartDisplayApp() {
  this.measureifc = new PythonProxy("/droid/json/charts/");
  this.root = DIV({id: "chartdisplayapp", "class": "applet"});
  var buttonbar = DIV({id: "buttonbar", class: "buttonbar"});
  var frame = createDOM("object", {id: "chartobject",
                                   data: "/media/images/charts/", 
                                   width: "720",
                                   height: "600",
                                   type: "text/html"}
                                   );
  this.root.appendChild(buttonbar);
  this.root.appendChild(frame);
};

ChartDisplayApp.prototype.destroy = function() {
  placeContent("extra", null);
};

