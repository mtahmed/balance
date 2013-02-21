#!/usr/bin/env python

# Standard imports
import sys
import os
import cgi
import cgitb
import re
import MySQLdb

# Custom imports
import settings

cgitb.enable()

print "Content-type: text/html"
print
username = os.environ['REMOTE_USER']

conn = MySQLdb.connect(host = settings.database_hostname,
                       user = settings.database_user,
                       passwd = settings.database_password,
                       db = settings.database_name)
cursor = conn.cursor()


def log(from_user, to_user, for_message, amount):
    '''
    Log the entry for the current user.
    '''
    cursor.execute('''INSERT INTO balance_logs VALUES (NOW(), %s, %s, %s, %s, %s)''',
                   (username, from_user, to_user, for_message, amount))
    return


def add_user(name):
    '''
    Add the user with name NAME to the database.
    '''
    users = get_all_users()
    if name in users:
        raise Exception("The user %s is already in the database." % name)
    cursor.execute('''INSERT INTO users VALUES (%s)''',
                   (name,))
    for user in users:
        create_new_balance(name, user)
    return


def get_all_users():
    '''
    Get a list of all the users we have in the databse.
    '''
    cursor.execute('''SELECT name FROM users''')
    rows = cursor.fetchall()
    return [row[0] for row in rows]


def resolve_prefix(prefix):
    '''
    Get the actual username for PREFIX of the username.
    '''
    users = get_all_users()
    # If the prefix is equal to some username...
    if prefix in users:
        return prefix
    matches = []
    pattern = re.compile(prefix)
    for user in users:
        if pattern.match(user):
            matches.append(user)
    if len(matches) > 1:
        print "error: ambigious name: %s" % from_user
        exit(0)
    elif len(matches) == 0:
        print "error: no matches for name: %s" % from_user
        exit(0)
    else:
        return matches[0]

def create_new_balance(person1, person2):
    '''
    Create an empty record for PERSON1 to PERSON2 and the other way.
    '''
    cursor.execute('''INSERT INTO balance VALUES (%s, %s, %s)''',
                   (person1, person2, 0))
    cursor.execute('''INSERT INTO balance VALUES (%s, %s, %s)''',
                   (person2, person1, 0))
    return


def get_balance(person1, person2):
    '''
    Get the amount PERSON1 owes PERSON2.
    '''
    cursor.execute('''SELECT amount FROM balance WHERE person1=%s AND person2=%s''',
                   (person1, person2))
    person1_to_person2 = cursor.fetchone()
    if person1_to_person2 is None:
        return None
    else:
        return person1_to_person2[0]


def update_balance(person1, person2, for_message, amount_str):
    '''
    Update the AMOUNT that PERSON1 owes PERSON2.
    '''
    if amount_str == 'none':
        amount = 0
    else:
        amount = float(eval(amount_str))

    if amount_str[0] in ('+', '-'):
        person1_to_person2 = get_balance(person1, person2)
        if person1_to_person2 is None:
            create_new_balance(person1, person2)
            person1_to_person2 = 0.0
        if person1_to_person2 + amount > 0.0:
            cursor.execute('''UPDATE balance SET amount=%s WHERE person1=%s AND person2=%s''',
                           (person1_to_person2 + amount, person1, person2))
        else:
            cursor.execute('''UPDATE balance SET amount=%s WHERE person1=%s AND person2=%s''',
                           (0.0, person1, person2))
            cursor.execute('''UPDATE balance SET amount=%s WHERE person1=%s AND person2=%s''',
                           (-1 * (person1_to_person2 + amount), person2, person1))
    else:
        cursor.execute('''UPDATE balance SET amount=%s WHERE person1=%s AND person2=%s''',
                       (amount, person1, person2))

    log(person1, person2, for_message, amount)
    return
    

def print_table():
    users = get_all_users()

    print """<div id='balance-table' style='margin: 0px; padding: 0px;'>"""
    print """<table>"""
    print """<tr>"""
    print """<td></td>"""
    for user in users:
        print """<td>%s</td>""" % user
    print """</tr>"""

    for person1 in users:
        print """<tr>"""
        print """<td>%s</td>""" % person1
        for person2 in users:
            if person1 == person2:
                print """<td></td>"""
                continue
            person1_to_person2 = get_balance(person1, person2)
            if person1_to_person2 == 0.0 or person1_to_person2 is None:
                print """<td></td>"""
            else:
                print """<td style='text-align: right;'>%.2f</td>""" % person1_to_person2
        print """</tr>"""
    
    print """</table>"""
    print """</div>"""
    return


def print_logs():
    cursor.execute('''SELECT * FROM balance_logs ORDER BY ts DESC LIMIT 50''')
    logs = cursor.fetchall()
    print """<h1>Logs</h1>"""
    print """<table>"""
    print """<tr><td>date</td><td>user</td><td>from</td><td>to</td><td>for</td><td>amount</td></tr>"""
    prev_log = None
    for log in logs:
        print """<tr>"""
        print """<td>%s</td>""" % log[0]
        # If the previous log had the same 'for' message and same amount,
        # then don't print the user this time.
        if prev_log is None:
            print """<td>%s</td>""" % log[1]
        elif (prev_log[4] == log[4] and
              prev_log[5] == log[5]):
            print """<td></td>"""
        else:
            print """<td>%s</td>""" % log[1]
        print """<td>%s</td>""" % log[2]
        print """<td>%s</td>""" % log[3]
        print """<td>%s</td>""" % log[4]
        if log[5] > 0:
            print """<td style='text-align: right;'>+%.2f</td>""" % log[5]
        else:
            print """<td style='text-align: right;'>%s</td>""" % log[5]
        print """</tr>"""
        prev_log = log
    print """</table>"""
    print """<br />"""
    print """<br />"""
    return


def print_form():
    users = get_all_users()

    print """
    <div style='margin-top: 15px;'>
        <input type='text' id='command-box' style='width: 296px; padding: 0px;' /> [Enter to submit]
        <br />
        <div id='status' style='height: 15px;  width: 300px; background-color: #ddd;'></div>
        <br />
        <br />
    """
    return


def print_examples():
    print """
        <h1>Examples</h1>
        szbokhar owes mtahmed $10:
        <br />
        <code>szbokhar owes mtahmed 10</code>
        <br />
        <br />
        szbokhar owes mtahmed $10 more:
        <br />
        <code>szbokhar owes mtahmed +10</code>
        <br />
        <br />
        szbokhar pays back mtahmed $10:
        <br />
        <code>szbokhar owes mtahmed -10</code>
        <br />
        <br />
        szbokhar pays back mtahmed all that he owes:
        <br />
        <code>szbokhar owes mtahmed 0</code>
        <br />
        or
        <br />
        <code>szbokhar owes mtahmed none</code>
        <br />
        <br />
        The command line also accepts unambigious prefixes of usernames.
        <br />
        So all these are equivalent (for users: [mtahmed, szbokhar, my4li])
        <br />
        <code>szbokhar owes mtahmed 0</code>
        <br />
        <code>szbokhar owes mt 0</code>
        <br />
        <code>s owes mt 0</code>
        <br />
        <code>sz owes mt 0</code>
        <br />
        <br />
        The command line also accepts lists.
        <br />
        Everyone owes mtahmed +$2
        <br />
        <code>szbokhar my4li blung owes mtahmed +2</code>
        <br />
        <br />
        The above can also be written using the 'all' keyword.
        <br />
        <code>all owes mtahmed +2</code>
        <br />
        <br />
        The 'for' keyword can be used to log reasons for updates.
        <br />
        <code>all owes mtahmed +10 for pizza</code>
        <br />
        <code>szbokhar owes mtahmed -10 for paid back</code>
    </div>
    """
    return


def print_body_head():
    print """
    <!DOCTYPE HTML>

    <html>

    <head>
    <script src='https://ajax.googleapis.com/ajax/libs/jquery/1.4/jquery.min.js'></script>
    <script src='https://ajax.googleapis.com/ajax/libs/jqueryui/1.8/jquery-ui.min.js'></script>
    <script src='https://csclub.uwaterloo.ca/~mtahmed/balance/commands.js'></script>
    <link rel='stylesheet' type='text/css' href='https://www.csclub.uwaterloo.ca/~mtahmed/css/style-main.css' />

    <style type='text/css'>
        body {
            font-size: 12px;
        }
        table {
            border-collapse: collapse;
            padding: 0px;
            margin: 0px;
        }
        tr {
            padding: 0px;
            margin: 0px;
        }
        td {
            padding: 5px;
        }
        table, th, td {
            border: 1px solid #999;
        }
        code {
            padding: 2px;
            font-family: monospace;
            background-color: #CCC;
        }
    </style>
    </head>

    <body>
    """
    print "User: %s" % username
    print "<br />"
    print "<br />"
    return


def print_body_foot():    
    print """
    </body>

    </html>
    """
    return


if __name__ == '__main__':
    if username not in get_all_users() and username not in settings.admin_users:
        print "Permission denied for user: %s" % username
        sys.exit(0)
    params = cgi.FieldStorage()
    command_str = ''
    if 'command' in params:
        command_str = params['command'].value

    users = get_all_users()

    for_index = command_str.find('for ')
    for_message = ""
    if for_index == -1:
        command_split = command_str.split(' ')
    else:
        command_split = command_str[:for_index - 1].split(' ')
        for_message = command_str[for_index+4:]

    # If there's no command...
    if command_split[0] == '':
        print_body_head()
        print """<h1>Balance</h1>"""
        print_table()
        print_form()
        print_logs()
        print_examples()
        print_body_foot()
    # If the command is add...
    elif command_split[0] == 'add':
        add_list = command_split[1:]
        for user in add_list:
            add_user(user)
        print_table()
    # Otherwise, it must be update.
    else:
        owes_index = command_split.index('owes')
        if command_split[0] == 'all':
            from_list = users
        else:
            from_list = command_split[:owes_index]
        to_list = command_split[owes_index + 1:len(command_split) - 1]
        # The user could be using prefixes of names; in that case, determine the actual name.
        from_list = [resolve_prefix(prefix) for prefix in from_list]
        to_list = [resolve_prefix(prefix) for prefix in to_list]

        amount_str = command_split[-1]
        for person1 in from_list:
            for person2 in to_list:
                update_balance(person1, person2, for_message, amount_str)
        print_table()
