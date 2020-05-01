"use strict";

var mySocket;
var journalEntryArray = [];
var filter = "";

$(document).ready(function() {

	if(!("WebSocket" in window)){
		console.log("browser support no web sockets");
		return;
	} else {
		initWebSockets();
	}

	cookieLoadView();
	cookieLoadFilter();
	initButtons();
	registerFilter();

	document.getElementById("logfilter").focus();
});

function registerFilter() {
	$("#logfilter").keyup(function() {
		filter = $(this).val();
		redrawJournalList();
		setCookie("journal-filter", filter);
	});
}

var journal_view = 'extended';

function cookieLoadView() {
  journal_view = getCookie("journal-view", 'extended');
  if (journal_view == 'extended') {
    $('#toggle-view-extended').closest('.btn').button('toggle');
  } else {
    $('#toggle-view-dense').closest('.btn').button('toggle');
  }
}

function cookieLoadFilter() {
	filter = getCookie("journal-filter", '');
	var text_field = document.getElementById("logfilter");
	text_field.value = filter;
}

function initButtons() {
  $('#sync-toggle').on('click', 'label.btn', function(e) {
    if (e.target.id == 'on') {
			mySocket.send("journal-sync-start");
    } else {
			mySocket.send("journal-sync-stop");
    }
    return
    if ($(this).hasClass('active')) {
      setTimeout(function() {
        $(this).removeClass('active').find('input').prop('checked', false);
      }.bind(this), 10);
    }
  });

	$('#toggle-view-extended').on('change', function () {
    journal_view = 'extended';
		redrawJournalList();
    setCookie("journal-view", 'extended');
	});

	$('#toggle-view-dense').on('change', function () {
    journal_view = 'dense';
		redrawJournalList();
    setCookie("journal-view", 'dense', 365);
	});

}

function wsOnOpen(event) {
	mySocket.send("history");
	mySocket.send("journal-sync-start");
}

// this is why JS is so f*cking stupid, see callsites
function addZero(x, n) {
	while (x.toString().length < n) {
		x = "0" + x;
	}
	return x;
}

function journalRealTimeToHuman(time) {
	// time is in microseconds, we need in milli,
	// which is fine for now
	var date = new Date(time / 1000);

	var year = date.getUTCFullYear();
	var month = date.getUTCMonth() + 1;
	var day = date.getUTCDate();

	var hours = addZero(date.getUTCHours(), 2);
	var minutes = addZero(date.getMinutes(), 2);
	var seconds = addZero(date.getSeconds(), 2);
	var milliseconds = addZero(date.getMilliseconds(), 3);
	return year + "-" + month + "-" + day + " " + hours + ':' +
		     minutes + ':' + seconds + "." + milliseconds;
}

function journalSaveNewEntry(entry) {
	// we do converations once, not every time we draw them
	var message = "no message";
	if ('MESSAGE' in entry) {
		message = entry['MESSAGE'];
	}

	// uid, gid and pid
	var uid = "unknown";
	if ('_UID' in entry) {
		uid = entry['_UID'];
	}
	var gid = "unknown";
	if ('_GID' in entry) {
		gid = entry['_GID'];
	}
	var pid = "unknown";
	if ('_PID' in entry) {
		pid = entry['_PID'];
	}

	// misc
	var transport = "unknown";
	if ('_TRANSPORT' in entry) {
		transport = entry['_TRANSPORT'];
	}
	var cmdline = "unknown";
	if ('_CMDLINE' in entry) {
		cmdline = entry['_CMDLINE'];
	}
	var comm = "unknown";
	if ('_COMM' in entry) {
		comm = entry['_COMM'];
	}

	// time
	var realtime = "error";
	var timestamp = new Date(2000, 1, 1);
	if ('__REALTIME_TIMESTAMP' in entry) {
		realtime = journalRealTimeToHuman(entry['__REALTIME_TIMESTAMP']);
		timestamp = new Date(entry['__REALTIME_TIMESTAMP'] / 1000);
	}

	var human_prio = "unknown"
	if ('PRIORITY' in entry) {
		var prio = entry['PRIORITY'];
		if (prio == 0) {
			human_prio = 'emerg';
		} else if (prio == 1) {
			human_prio = 'alert';
		} else if (prio == 2) {
			human_prio = 'crit';
		} else if (prio == 3) {
			human_prio = 'err';
		} else if (prio == 4) {
			human_prio = 'warning';
		} else if (prio == 5) {
			human_prio = 'notice';
		} else if (prio == 6) {
			human_prio = 'info';
		} else if (prio == 7) {
			human_prio = 'debug';
		}
	}

    var element = {
        message: message,
        priority: human_prio,
        uid: uid,
        gid: gid,
        pid: pid,
        cmdline: cmdline,
        transport: transport,
        comm: comm,
        realtime: realtime,
        timestamp: timestamp
    };

	  if (journalEntryArray.length >= 50000) {
			// just to limit the amount of recorded log
			// entries for the browser, if not the browser
			// will run out of memory
			journalEntryArray.shift();
		}

    journalEntryArray.push(element);
}

function itemSelectPriorityColor(entry) {
    switch (entry.priority) {
        case "emerg":
            return 'item-emerg';
        case "alert":
            return 'item-alert';
        case "crit":
            return 'item-crit';
        case "err":
            return 'item-err';
        case "warning":
            return 'item-warning';
        case "notice":
            return 'item-notice';
        case "info":
            return 'item-info';
        case "debug":
            return 'item-debug';
        default:
            return 'item-unknown';
    }
}

function journalEntryConstructSubtitle(entry) {
	var str = "comm: <b>" + entry.comm
		+ '</b> / priority: <b>' + entry.priority
	  + '</b> / pid: <b>' +  entry.pid
	  + '</b> / uid: <b>' +  entry.uid
	  + '</b> / gid: <b>' +  entry.gid
	  + '</b> / cmdline: <b>' +  entry.cmdline
	  + '</b> / transport: <b>' +  entry.transport
	  + '</b>';
	return str
}

function processJournalEntriesData(data) {
    for (let s of data) {
        journalSaveNewEntry(s);
    }
    redrawJournalList();
}

function filter_processing(filter_word, journalEntry) {
	// -1 corrupt - ignore, go on
	// 0: filter do not apply (pid:100 != 202)
	// 1: filter matches

	if (filter_word.includes(":")) {
		// complex filter
		var token = filter_word.split(":");
		if (token.length != 2) {
			// filter_word seems corrupt (e.g. "pid:123:garbage")
			return -1;
		}
		const key = token[0].toLowerCase();
		const value = token[1].toLowerCase();
		switch (key) {
			case "uid":
				if (journalEntry.uid == value) {
					return 1;
				} else {
					return 0;
				}
				break
			case "gid":
				if (journalEntry.gid == value) {
					return 1;
				} else {
					return 0;
				}
				break
			case "pid":
				if (journalEntry.pid == value) {
					return 1;
				} else {
					return 0;
				}
				break
			case "timestamp":
				// we do incremental search, just to beautify
				// the user experience, it slowly filters out more entry
				// the more the user types in
				if (journalEntry.timestamp.toLowerCase().includes(value.toLowerCase())) {
					return 1;
				} else {
					return 0;
				}
				break
			case "realtime":
				// we do incremental search, just to beautify
				// the user experience, it slowly filters out more entry
				// the more the user types in
				if (journalEntry.realtime.toLowerCase().includes(value.toLowerCase())) {
					return 1;
				} else {
					return 0;
				}
				break
			case "transport":
				// we do incremental search, just to beautify
				// the user experience, it slowly filters out more entry
				// the more the user types in
				if (journalEntry.transport.toLowerCase().includes(value.toLowerCase())) {
					return 1;
				} else {
					return 0;
				}
				break
			case "cmdline":
				// we do incremental search, just to beautify
				// the user experience, it slowly filters out more entry
				// the more the user types in
				if (journalEntry.cmdline.toLowerCase().includes(value.toLowerCase())) {
					return 1;
				} else {
					return 0;
				}
				break
			case "priority":
				if (journalEntry.priority.toLowerCase().includes(value.toLowerCase())) {
					return 1;
				} else {
					return 0;
				}
			case "comm":
				if (journalEntry.comm.toLowerCase().includes(value.toLowerCase())) {
					return 1;
				} else {
					return 0;
				}
			default:
				// unknown, unhandled key
				return -1;
				break;
		}
	} else {
		// simple word filter
		// we do a substring search, probably the most
		// usefull thing
		if (journalEntry.message.toLowerCase().includes(filter_word.toLowerCase())) {
			return 1;
		}
		return 0;
	}
}

/**
 * Returns false if line is not to be filtered,
 * true otherwise
 */
function is_filtered(journalEntry) {
	var all_filters = [];

	// short circuit, early return
	if (filter == "")
		return false;

	var filter_words = filter.split(" ");
  for (const filter_word of filter_words) {
		if (filter_word == "")
			continue;
	
		const result = filter_processing(filter_word, journalEntry);
		switch (result) {
			case -1:
				break
			case 0:
				all_filters.push(false);
				break;
			case 1:
				all_filters.push(true);
				break;
		}
	}

	if (!all_filters.includes(false)) {
		return false;
	}
	return true;
}

var journalInfoDb = new Object();

function journalInfoResetDb() {
	journalInfoDb.entries = 0;
	journalInfoDb.first_ts = 0;
	journalInfoDb.last_ts = 0;
}

function dateDiff(date1, date2) {
    var diff = (date2 - date1) / 1000;
    diff = Math.abs(Math.floor(diff));

    var days = Math.floor(diff/(24*60*60));
    var leftSec = diff - days * 24*60*60;

    var hrs = Math.floor(leftSec/(60*60));
    var leftSec = leftSec - hrs * 60*60;

    var min = Math.floor(leftSec/(60));
    var leftSec = leftSec - min * 60;

    return "" + days + "d, " + hrs + "h, " + min + "m, " + leftSec + "s";
}

function journalInfoUpdateDb(entry) {
	journalInfoDb.entries += 1;
	if (journalInfoDb.last_ts == 0)
		journalInfoDb.last_ts = entry.timestamp; 
	journalInfoDb.first_ts = entry.timestamp;
}

function journalInfoResetRedraw() {
	var str = "";
	var text_field = document.getElementById("journal-info");

	if (journalInfoDb.entries != 0) {
		str = "Entries displayed: <b>" + journalInfoDb.entries + "</b><br />" +
					"Last: <b>" + journalInfoDb.last_ts.toUTCString() + "</b><br />" +
					"First: <b>" + journalInfoDb.first_ts.toUTCString() + "</b><br />" +
			    "Time Delta: <b>" + dateDiff(journalInfoDb.first_ts, journalInfoDb.last_ts) + "</b>";
	}
	text_field.innerHTML = str;
}

function redrawJournalListExtended() {
	var newstr = ""
	for (var i = journalEntryArray.length - 1; i > 0; i--) {
	  // if a filter was set we ignore all messages not
		// matching the string, we using includes() here,
		// no fancy regex, etc.
		if (is_filtered(journalEntryArray[i]))
			continue

		journalInfoUpdateDb(journalEntryArray[i]);

		newstr = newstr
			+ '<a href="#myModal" data-toggle="modal" class="list-group-item list-group-item-action flex-column align-items-start '
		  + itemSelectPriorityColor(journalEntryArray[i]) + '">'
		  + '<div class="d-flex w-100 justify-content-between"> <h5 class="mb-1">'
			+ journalEntryArray[i].message
		  + '</h5><small>'
		  + journalEntryArray[i].realtime
			+ ' </small></div><small class="text-supermuted">'
		  + journalEntryConstructSubtitle(journalEntryArray[i])
		  + '</small></a>';
	}
	let output = document.getElementById("anchor-journal");
	output.innerHTML = newstr;
}

var timestampPrev;

function timestampDeltaInit() {
  timestampPrev = null;
}

function timestampDeltaCalc(time) {
  if (timestampPrev == null) {
    timestampPrev = time;
    return "↥ ∞";
  }

  var delta = parseFloat((timestampPrev - time) / 1000).toFixed(3);
  timestampPrev = time;
  return "↥ " + delta + "s";
}

function redrawJournalListDense() {
  timestampDeltaInit();
	var newstr = ""
	for (var i = journalEntryArray.length - 1; i > 0; i--) {
		if (is_filtered(journalEntryArray[i]))
			continue

		journalInfoUpdateDb(journalEntryArray[i]);

    var delta_to_pref = timestampDeltaCalc(journalEntryArray[i].timestamp);
		newstr = newstr
			+ '<a href="#myModal" data-toggle="modal" class="nullspacer list-group-item list-group-item-action flex-column align-items-start '
		  + itemSelectPriorityColor(journalEntryArray[i]) + '">'
		  + '<div class="d-flex w-100 justify-content-between"> <h5 class="mb-1">'
			+ journalEntryArray[i].message
		  + '</h5><small>'
		  + delta_to_pref
			+ ' </small></div>'
		  + '</a>';
	}
	let output = document.getElementById("anchor-journal");
	output.innerHTML = newstr;
}


function redrawJournalList() {
	journalInfoResetDb();
  if (journal_view == 'extended') {
    redrawJournalListExtended();
  } else {
    redrawJournalListDense();
  }
	journalInfoResetRedraw();
}

function wsOnMessage(event) {
	var jdata = JSON.parse(event.data);
	if ('data-log-entries' in jdata) {
		processJournalEntriesData(jdata['data-log-entries']);
	} else {
		console.log("data not handled");
	}
}

function initWebSockets() {
	try {

		try {
			mySocket = new WebSocket('ws://' + window.location.host + '/ws-journal');
		}
		catch(err) {
			mySocket = new WebSocket('wss://' + window.location.host + '/ws-journal');
		}
		mySocket.onmessage = wsOnMessage;
		mySocket.onopen    = wsOnOpen;

	} catch(exception){
		console.log('Error' + exception);
	}
}

