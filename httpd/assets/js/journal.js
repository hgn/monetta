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
	initButtons();
	registerFilter();
});

function registerFilter() {
	$("#logfilter").keyup(function() {
		filter = $(this).val();
		redrawJournalList();
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
	mySocket.send("info");
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

	var year = date.getFullYear();
	var month = date.getMonth() + 1;
	var day = date.getDate();

	var hours = addZero(date.getHours(), 2);
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
	if ('__REALTIME_TIMESTAMP' in entry) {
		realtime = journalRealTimeToHuman(entry['__REALTIME_TIMESTAMP']);
	}

	var timestamp = new Date(2000, 1, 1);
	if ('__REALTIME_TIMESTAMP' in entry) {
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
	var str = "com: " + entry.comm
		+ ' / prio: ' + entry.priority
	  + ' / pid: ' +  entry.pid
	  + ' / uid: ' +  entry.uid
	  + ' / gid: ' +  entry.gid
	  + ' / cmdline: ' +  entry.cmdline
	  + ' / transport: ' +  entry.transport;
	return str
}

function processJournalEntriesData(data) {
    for (let s of data) {
        journalSaveNewEntry(s);
    }
    redrawJournalList();
}

function processJournalEntryData(data) {
  journalSaveNewEntry(data);
  redrawJournalList();
}

function redrawJournalListExtended() {
	var newstr = ""
	for (var i = journalEntryArray.length - 1; i > 0; i--) {
	  // if a filter was set we ignore all messages not
		// matching the string, we using includes() here,
		// no fancy regex, etc.
		if (filter != "") {
			if (!journalEntryArray[i].message.toLowerCase().includes(filter.toLowerCase()))
				continue
		}
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
	  // if a filter was set we ignore all messages not
		// matching the string, we using includes() here,
		// no fancy regex, etc.
		if (filter != "") {
			if (!journalEntryArray[i].message.toLowerCase().includes(filter.toLowerCase()))
				continue
		}
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
  if (journal_view == 'extended') {
    redrawJournalListExtended();
  } else {
    redrawJournalListDense();
  }
}

function processJournalInfoData(data) {
    if ('list-comm' in data) {
        var comm_entries = data['list-comm'].sort().reverse();
        var newstr = '<div class="btn-group" role="group" aria-label="Basic example">'
            + '<button type="button" class="btn btn-secondary btn-sm">Deselect All</button>'
            + '<button type="button" class="btn btn-secondary btn-sm">Select All</button>'
            + '</div><hr />'
        for (var i = comm_entries.length - 1; i > 0; i--) {
            newstr = newstr +
                '<div class="form-check"><label class="form-check-label">' +
                '<input class="form-check-input" type="checkbox" value=""> ' +
                comm_entries[i] +
                '</label></div>';
        }
        var output = document.getElementById("process-list");
        output.innerHTML = newstr;
    }
}

function wsOnMessage(event) {
	var jdata = JSON.parse(event.data);
	if ('data-log-entry' in jdata) {
		processJournalEntryData(jdata['data-log-entry']);
	} else if ('data-log-entries' in jdata) {
		processJournalEntriesData(jdata['data-log-entries']);
	} else if ('data-info' in jdata) {
		processJournalInfoData(jdata['data-info']);
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

