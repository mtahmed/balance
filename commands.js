function load_balance() {
  $('#balance-table').html("Loading...");
  $.get('balance.py?command=' + encodeURIComponent("print_balance"),
    function(data) {
        $('#balance-table').html(data);
    }
  );
}

function load_logs(filter) {
  $('#logs-table').html("Loading...");

  if (filter != '')
    command_string = filter;
  else
    command_string = 'print_logs';

  $.get('balance.py?command=' + encodeURIComponent(command_string),
    function(data) {
        $('#logs-table').html(data);
    }
  );
}

function print_error(msg) {
  $('#status').html('<span style="color:red;">' + msg + '</span>')
              .delay(8000)
              .queue(function() { $(this).html('') });
}

function print_done(msg) {
  $('#status').html('done').delay(5000).queue(function() { $(this).html('') });
}

$(document).ready(
  function() {
    $('#command-box').focus();
    $('#command-box').keyup(
      function(e) {
        if (e.keyCode == 13) {
          var command_string = $(this).val();
          if (command_string.substring(0, 6) == 'filter') {
            load_logs(command_string);
            return;
          }
          $.get('balance.py?command=' + encodeURIComponent(command_string),
            function(data) {
              if (data.substring(0, 5) != 'error') {
                print_done();
                load_balance();
                load_logs('');
              } else {
                print_error(data);
              }
              $('#command-box').val('');
            }
          );
        }
      }
    );
  }
);
