"use strict";

var ws_socket;


$(document).ready(function() {

    // just draw something, just to
    // make the user experience less
    // flickering
    setupInitialGraphs();


	if(!("WebSocket" in window)){
		console.log("browser support no web sockets");
		return;
	} else {
		initWebSockets();
	}
});



function dataCpuGraph(data, data_time) {

	var height = 300;
	var width = document.getElementById('chart-cpu').offsetWidth;

	// just remove the old svg and draw a new one
	// no clue how to implement transistions ...
  var svgParent =	document.getElementById("chart-cpu");
	while (svgParent.hasChildNodes()) {
		    svgParent.removeChild(svgParent.firstChild);
	}

	var chartDiv = document.getElementById("chart-cpu");
	var svg = d3.select(chartDiv).append("svg");
	svg.attr("width",width).attr("height",height);


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

	var data_y_min = d3.min(data, function(c) { return d3.min(c.values, function(d) { return d.load; }); })
	var data_y_max = d3.max(data, function(c) { return d3.max(c.values, function(d) { return d.load; }); })
	var data_y_max_final = d3.max([data_y_max, 100]);

	y.domain([
		data_y_min, data_y_max_final
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
    ws_socket.send("start-cpu-utilization");
    ws_socket.send("get-meminfo");
}

function sleep(ms) {
	return new Promise(resolve => setTimeout(resolve, ms));
}


async function d3Debugging() {

	var parseTimeT = d3.timeParse("%Y-%m-%d %H:%M:%S");

    var time1 = parseTimeT('2000-1-1 10:10:10');
	var time2 = parseTimeT('2000-1-1 10:11:11');
	var time3 = parseTimeT('2000-1-1 10:12:11');

	var data_values = [
		{'id' : 'New York', 'values' : [
			{ 'date' : time1, 'load' : 30},
			{ 'date' : time2, 'load' : 34 },
		]},
		{'id' : 'San Francisco', 'values' : [
			{ 'date' : time1, 'load' : 40},
			{ 'date' : time2, 'load' : 34 },
		]},
		{'id' : 'Austin', 'values' : [
			{ 'date' : time1, 'load' : 50},
			{ 'date' : time2, 'load' : 35 },
		]}
	]
	var data_time = [time1, time2];

	//dataCpuGraph(data_values, data_time);

	await sleep(1000);

	var data_values = [
		{'id' : 'New York', 'values' : [
			{ 'date' : time1, 'load' : 30},
			{ 'date' : time2, 'load' : 34 },
			{ 'date' : time3, 'load' : 14 },
		]},
		{'id' : 'San Francisco', 'values' : [
			{ 'date' : time1, 'load' : 40},
			{ 'date' : time2, 'load' : 34 },
			{ 'date' : time3, 'load' : 44 }
		]},
		{'id' : 'Austin', 'values' : [
			{ 'date' : time1, 'load' : 50},
			{ 'date' : time2, 'load' : 35 },
			{ 'date' : time3, 'load' : 35 }
		]}
	]
	data_time = [time1, time3];

	dataCpuGraph(data_values, data_time);
}

// limit to 2 minutes ...
var cpu_limit_times = 60 * 2

function limitCpuRecordData(data) {
	var date = null;
	for (var i = 0; i < data.length; i++) {
		if (data[i].values.length > cpu_limit_times) {
			data[i].values.shift();
		}
		date = data[0].values[0].date;
	}
	return date;
}

var cpu_load_data = [];
var cpu_load_date_initial = null;

function processCpuLoad(data) {

	var number_of_values = 0;
	var parseTimeT = d3.timeParse("%Y-%m-%d %H:%M:%S");

	var date = parseTimeT(data['time']);

	var new_data_set = [];
	if (!cpu_load_date_initial) {
		cpu_load_date_initial = date;
	}

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

	// limit the data set to n
	var updated_initial = limitCpuRecordData(cpu_load_data);
	if (updated_initial != null)
		cpu_load_date_initial = updated_initial;

	if (number_of_values > 1) {
		// just to ignore loading graphs with with datapoint,
		// wait at least for second iteration.
		var date_range = [cpu_load_date_initial, date];
		dataCpuGraph(cpu_load_data, date_range);
	}
}

function wsOnMessage(event) {
			var jdata = JSON.parse(event.data);
			if ('cpu-load' in jdata) {
				processCpuLoad(jdata['cpu-load']);
            } else if ('meminfo' in jdata) {
                processMeminfoData(jdata['meminfo'])
			} else {
				console.log("data not handled");
			}
}

function initWebSockets() {
	try {
		console.log("use unencryped web socket for data exchange");
		ws_socket = new WebSocket('ws://' + window.location.host + '/ws-utilization');
	}
	catch(err) {
		try {
			ws_socket = new WebSocket('wss://' + window.location.host + '/ws-utilization');
		} catch(exception){
			console.log('Error' + exception);
		}
	}

	ws_socket.onmessage = wsOnMessage;
	ws_socket.onopen    = wsOnOpen;
}


// memory chart
function dataMeminfoGraph(data) {

    var height = 300;
    var width = document.getElementById('chart-memory').offsetWidth;
    var radius = Math.min(width, height) / 2;


    // just remove the old svg and draw a new one
    // no clue how to implement transistions ...
    var chartDiv =	document.getElementById("chart-memory");
    while (chartDiv.hasChildNodes()) {
        chartDiv.removeChild(chartDiv.firstChild);
    }

    var svg = d3.select(chartDiv).append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

    var color = d3.scaleOrdinal(["#98abc5", "#8a89a6", "#7b6888", "#6b486b", "#a05d56", "#d0743c", "#ff8c00"]);

    var arc = d3.arc()
        .outerRadius(radius - 10)
        .innerRadius(0);

    var labelArc = d3.arc()
        .outerRadius(radius - 40)
        .innerRadius(radius - 40);

    var pie = d3.pie()
        .sort(null)
        .value(function(d) { return d.presses; })(data);

    var g = svg.selectAll(".arc")
        .data(pie)
        .enter().append("g")
        .attr("class", "arc");

    g.append("path")
        .attr("d", arc)
        .style("fill", function(d) { return color(d.data.letter); });

    g.append("text")
			.attr("transform", function(d) { return "translate(" + labelArc.centroid(d) + ")"; })
			.attr("dy", ".35em")
			.style("font", "14px sans-serif")
			.attr("text-anchor", "middle")
			.text(function(d) { return d.data.letter; })
		//.style("text-shadow", "0 1px 0 #fff, 1px 0 0 #000, 0 -1px 0 #fff, -1px 0 0 #fff")
			.style("fill", "#333");
}

function convertRawMeminfoData(rawData) {
    var ret = [];

    var usedDiff = rawData['MemTotal'] - rawData['MemFree']
    var usedTitle = 'Used Memory: ' + prettyNumber(usedDiff);

    var freeDiff = parseInt(rawData['MemFree']);
    var freeTitle = 'Free Memory: ' + prettyNumber(freeDiff);

	  console.log(rawData['MemTotal']);
	  console.log(freeDiff);

    ret.push({letter : freeTitle, presses : freeDiff});
    ret.push({letter : usedTitle, presses : usedDiff});

    return ret;
}

function initialMeminfoData(rawData) {
    var ret = [];

    var usedDiff = 1
    var usedTitle = 'Used Memory: unknown';

    var freeDiff = 2;
    var freeTitle = 'Free Memory: unknown';

    ret.push({letter : freeTitle, presses : freeDiff});
    ret.push({letter : usedTitle, presses : usedDiff});

    return ret;
}

function processMeminfoData(rawData) {
    var pieGraphData = convertRawMeminfoData(rawData['data']);
    dataMeminfoGraph(pieGraphData);
}

function setupInitialMeminfoGraph() {
    var pieGraphData = initialMeminfoData();
    dataMeminfoGraph(pieGraphData);
}

function setupInitialGraphs() {
    setupInitialMeminfoGraph();
}

function prettyNumber(pBytes) {
    // Handle some special cases
    if(pBytes == 0) return '0 Bytes';
    if(pBytes == 1) return '1 Byte';
    if(pBytes == -1) return '-1 Byte';

    var bytes = Math.abs(pBytes)
		var orderOfMagnitude = Math.pow(2, 10);
		var abbreviations = ['Bytes', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
    var i = Math.floor(Math.log(bytes) / Math.log(orderOfMagnitude));
    var result = (bytes / Math.pow(orderOfMagnitude, i));

    if(pBytes < 0) {
        result *= -1;
    }

    if(result >= 99.995 || i==0) {
        return result.toFixed(0) + ' ' + abbreviations[i];
    } else {
        return result.toFixed(2) + ' ' + abbreviations[i];
    }
}
