"use strict";

var ws_socket;


$(document).ready(function() {

	if(!("WebSocket" in window)){
		console.log("browser support no web sockets");
		return;
	} else {
		initWebSockets();
	}
});



function loadGraph(data, data_time) {

	// just remove the old svg and draw a new one
	// no clue how to implement transistions ...
	d3.select("svg").remove();
	var chartDiv = document.getElementById("chart");
	var svg = d3.select(chartDiv).append("svg");
	svg.attr("width",860).attr("height",500);


	var margin = {top: 20, right: 80, bottom: 30, left: 50},
		width = svg.attr("width") - margin.left - margin.right,
		height = svg.attr("height") - margin.top - margin.bottom,
		g = svg.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");

	var x = d3.scaleTime().range([0, width]),
		y = d3.scaleLinear().range([height, 0]),
		z = d3.scaleOrdinal(d3.schemeCategory10);

	var line = d3.line()
		.curve(d3.curveBasis)
		.x(function(d) { return x(d.date); })
		.y(function(d) { return y(d.load); });


	x.domain(data_time);

	y.domain([
		d3.min(data, function(c) { return d3.min(c.values, function(d) { return d.load; }); }),
		d3.max(data, function(c) { return d3.max(c.values, function(d) { return d.load; }); })
	]);

	z.domain(data.map(function(c) { return c.id; }));

	g.append("g")
		.attr("class", "axis axis--x")
		.attr("transform", "translate(0," + height + ")")
		.call(d3.axisBottom(x));

	g.append("g")
		.attr("class", "axis axis--y")
		.call(d3.axisLeft(y))
		.append("text")
		.attr("transform", "rotate(-90)")
		.attr("y", 6)
		.attr("dy", "0.71em")
		.attr("fill", "#000")
		.text("Load %");

	var cpu = g.selectAll(".cpu")
		.data(data)
		.enter().append("g")
		.attr("class", "cpu");

	cpu.append("path")
		.attr("class", "line")
		.attr("d", function(d) { return line(d.values); })
		.style("stroke", function(d) { return z(d.id); });

	cpu.append("text")
		.datum(function(d) { return {id: d.id, value: d.values[d.values.length - 1]}; })
		.attr("transform", function(d) { return "translate(" + x(d.value.date) + "," + y(d.value.load) + ")"; })
		.attr("x", 3)
		.attr("dy", "0.35em")
		.style("font", "10px sans-serif")
		.text(function(d) { return d.id; });
}

function wsOnOpen(event) {
    ws_socket.send("start");
}


var cpu_load_data = [];
var cpu_load_date_data = [];

function processCpuLoad(data) {

	var number_of_values = 0;
	var parseTimeT = d3.timeParse("%Y-%m-%d %H:%M:%S");

	var date = parseTimeT(data['time']);

	var new_data_set = [];
	cpu_load_date_data.push(date);

	for (var key in data['data']){
		if (key == 'cpu') {
			// we don't want to graph the
			// cumulative cpu usage, we want to
			// graph the particular cpus, so ignore this one
			continue;
		}
		// generate a new data set
		var new_set = {
			date : date,
			load : data['data'][key]
		};

		// (1)
		// we will add the data set here if the actual
		// cpu id is in the set (just append the data)
		// This is what happens likely, only the first
		// iteration will bypass this.
		var found = false;
		for (var i = 0; i < cpu_load_data.length; i++) {

			if (cpu_load_data[i].values.length > number_of_values) {
				number_of_values = cpu_load_data[i].values.length;
			}

			if (cpu_load_data[i].id == key) {
				cpu_load_data[i].values.push(new_set);
				found = true;
				break;
			}
		}

		// (2)
		// or if not - new data - we create also a
		// new container and add the data
		if (!found) {
			var major = {
				id : key,
				values : [new_set]
			}
			cpu_load_data.push(major);
		}
	}

	if (number_of_values > 1) {
		// just to ignore loading graphs with with datapoint,
		// wait at least for second iteration.
		loadGraph(cpu_load_data, cpu_load_date_data);
	}

	return;





	var data_values = [
		{'id' : 'New York', 'values' : [{'date' : parseTimeT('2000-1-1 10:10:10'), 'load' : 30}, { 'date' : parseTimeT('2000-1-1 10:11:11'), 'load' : 34 }, { 'date' : parseTimeT('2000-1-1 10:12:11'), 'load' : 14 },  ]},
		{'id' : 'San Francisco', 'values' : [{'date' : parseTimeT('2000-1-1 10:10:10'), 'load' : 40}, { 'date' : parseTimeT('2000-1-1 10:11:11'), 'load' : 34 }, { 'date' : parseTimeT('2000-1-1 10:12:11'), 'load' : 44 } ]},
		{'id' : 'Austin', 'values' : [{'date' : parseTimeT('2000-1-1 10:10:10'), 'load' : 50}, { 'date' : parseTimeT('2000-1-1 10:11:11'), 'load' : 35 }, { 'date' : parseTimeT('2000-1-1 10:12:11'), 'load' : 35 } ]},
		{'id' : 'Berlin', 'values' : [{'date' : parseTimeT('2000-1-1 10:10:10'), 'load' : 0.0}, { 'date' : parseTimeT('2000-1-1 10:11:11'), 'load' : 10.2012021 }, { 'date' : parseTimeT('2000-1-1 10:12:11'), 'load' : 13.2012021 } ]},
	]
	var data_time = [parseTimeT('2000-1-1 10:10:10'), parseTimeT('2000-01-01 10:11:11'), parseTimeT('2000-1-1 10:12:11')];


	//loadGraph(data_values, data_time);

}

function wsOnMessage(event) {
			var jdata = JSON.parse(event.data);
			if ('cpu-load' in jdata) {
				processCpuLoad(jdata['cpu-load']);
			} else {
				console.log("data not handled");
			}
}

function initWebSockets() {
	try {
		ws_socket = new WebSocket('ws://' + window.location.host + '/ws-resource');
	}
	catch(err) {
		try {
			ws_socket = new WebSocket('wss://' + window.location.host + '/ws-resouce');
		} catch(exception){
			console.log('Error' + exception);
		}
	}

	ws_socket.onmessage = wsOnMessage;
	ws_socket.onopen    = wsOnOpen;
}
