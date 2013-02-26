$(document).ready(
  function() {
    $('#command-box').focus();
    $('#command-box').keyup(
      function(e) {
        if (e.keyCode == 13) {
          $.get('balance.py?command=' + encodeURIComponent($(this).val()),
            function(data) {
              if (data.substring(0, 5) != 'error') {
                $('#status').html('done').delay(5000).queue(function() { $(this).html('') });
                $('#balance-table').html(data);
              } else {
                $('#status').html('<span style="color:red;">' + data + '</span>')
                            .delay(8000)
                            .queue(function() { $(this).html('') });
              }
              $('#command-box').val('');
            }
          );
          return false;
        }
      }
    );
  }
);
