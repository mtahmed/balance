#!/usr/bin/env python

# Make sure division is always floating point.
from __future__ import division

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

def error(msg):
    print "error:", msg
    sys.exit(0)


def log(from_user, to_user, for_message, amount):
    '''
    Log the entry for the current user.
    '''
    cursor.execute('INSERT INTO balance_logs VALUES (NULL, NOW(), %s, %s, %s, %s, %s)',
                   (username, from_user, to_user, for_message, amount))
    return


def add_user(name):
    '''
    Add the user with name NAME to the database.
    '''
    users = get_all_users()
    if name in users:
        error("The user %s is already in the database." % name)
    cursor.execute('''INSERT INTO users VALUES (%s)''',
                   (name,))
    for user in users:
        create_new_balance(name, user)
    return


def remove_user(name):
    '''
    Remove the user with name NAME from the database.
    '''
    users = get_all_users()
    if name not in users:
        error("The user %s is not in the database." % name)
    # See if there is an existing balance
    if not is_balance_free(name):
        error("The user %s has an outstanding balance." % name)
    cursor.execute('''DELETE FROM users WHERE name=%s''',
                   (name,))
    delete_old_balance(name)
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
        error("ambigious prefix: %s" % prefix)
    elif len(matches) == 0:
        error("no matches for name: %s" % prefix)
    else:
        return matches[0]


def create_new_balance(user1, user2):
    '''
    Create an empty record for USER1 to USER2 and the other way.
    '''
    cursor.execute('''INSERT INTO balance VALUES (%s, %s, %s)''',
                   (user1, user2, 0))
    cursor.execute('''INSERT INTO balance VALUES (%s, %s, %s)''',
                   (user2, user1, 0))
    return


def delete_old_balance(user):
    '''
    Delete an existing record for USER to and from any other user.
    '''
    cursor.execute('''DELETE FROM balance WHERE user1=%s OR user2=%s''',
                   (user, user))
    return


def is_balance_free(name):
    '''
    Determine whether a user has no money owed or owing with any other user.
    '''
    users = get_all_users()
    for user in users:
        if get_balance(name, user) or get_balance(user, name):
            return False
    return True


def is_user_exists(name):
    '''
    Determine whether a user exists.
    '''
    users = get_all_users()
    return name in users


def get_balance(from_user, to_user):
    '''
    Get the amount PERSON1 owes PERSON2.
    '''
    cursor.execute('''SELECT amount FROM balance WHERE from_user=%s AND to_user=%s''',
                   (from_user, to_user))
    from_user_to_to_user = cursor.fetchone()
    if from_user_to_to_user is None:
        return None
    else:
        return from_user_to_to_user[0]


def update_balance(from_user, to_user, for_message, amount_str, log_record=True):
    '''
    Update the AMOUNT that FROM_USER owes TO_USER.
    '''
    if from_user == to_user:
        error("a user cannot owe themself")

    # Just set it to 0 in case someone paid back the whole amount.
    if amount_str in ('none', '0'):
        cursor.execute('''UPDATE balance SET amount=0 WHERE from_user=%s AND to_user=%s''',
                        (from_user, to_user))
        return

    if amount_str == 'none':
        amount = 0
    else:
        try:
            amount = float(eval(amount_str, {"__builtins__":None}, {}))
        except:
            error("invalid math expression %s." % amount_str)

    from_user_to_to_user = get_balance(from_user, to_user)
    to_user_to_from_user = get_balance(to_user, from_user)
    if from_user_to_to_user is None or to_user_to_from_user is None:
        create_new_balance(from_user, to_user)
        from_user_to_to_user = 0.0
        to_user_to_from_user = 0.0

    final_amount = amount + from_user_to_to_user - to_user_to_from_user
    if final_amount > 0.0:
        cursor.execute('''UPDATE balance SET amount=%s WHERE from_user=%s AND to_user=%s''',
                        (0.0, to_user, from_user))
        cursor.execute('''UPDATE balance SET amount=%s WHERE from_user=%s AND to_user=%s''',
                        (final_amount, from_user, to_user))
    elif final_amount <= 0.0:
        cursor.execute('''UPDATE balance SET amount=%s WHERE from_user=%s AND to_user=%s''',
                        (0.0, from_user, to_user))
        cursor.execute('''UPDATE balance SET amount=%s WHERE from_user=%s AND to_user=%s''',
                        ((-1 * final_amount), to_user, from_user))

    if log_record:
        log(from_user, to_user, for_message, amount)
    return


def undo(record_id, delete=False):
    '''
    Undo the transaction with log record id `record_id`.
    '''
    cursor.execute('''SELECT * FROM balance_logs WHERE id=%s''', (record_id,))
    rowcount = cursor.rowcount
    if rowcount <= 0:
        error("no record with id %s found" % string(record_id))
    elif rowcount > 1:
        error("NOOOOOOOOOOOOOOOOOOOOOoooooooooooo: more than one records match")
    else:
        record = cursor.fetchone()

    from_user = record[3]
    to_user = record[4]
    for_message = "UNDO %d" % record_id
    amount_str = str(-1 * record[6])

    if delete:
        cursor.execute('''DELETE FROM balance_logs where id=%s''', (record_id))

    # If delete, then don't log_record.
    log_record = not delete

    # Don't undo if a user doesn't exist
    if not is_user_exists(from_user) or not is_user_exists(to_user):
        error("One of the given users don't exist. Cannot undo.")

    update_balance(from_user, to_user, for_message, amount_str, log_record)
    return


def edit_comment(record_id, new_comment):
    '''
    Edit the comment associated with a transaction with log record id 'record_id'
    '''
    cursor.execute('''SELECT * from balance_logs WHERE id=%s''', (record_id,))
    rowcount = cursor.rowcount
    if rowcount <= 0:
        error("no record with id %s found" % string(record_id))
    elif rowcount > 1:
        error("NOOOOOOOOOOOOOOOOOOOOOoooooooooooo: more than one records match")
    else:
        cursor.execute('''UPDATE balance_logs SET for_message=%s WHERE id=%s''', (new_comment, record_id))
    return


def print_balance():
    users = get_all_users()

    print """<div id='balance-table'>"""
    print """<table>"""
    print """<tr>"""
    print """<td style='font-weight: bold; font-size: 20px; text-align: center;'>&#x21b1;</td>"""
    for user in users:
        if user in settings.admin_users:
            print """<td style='text-decoration: underline;'>%s</td>""" % user
        else:
            print """<td>%s</td>""" % user
    print """</tr>"""

    for from_user in users:
        print """<tr>"""
        print """<td>%s</td>""" % from_user
        for to_user in users:
            if from_user == to_user:
                print """<td style='background-color:#d1d1d1;'></td>"""
                continue
            from_user_to_to_user = get_balance(from_user, to_user)
            if from_user_to_to_user < 0.01 or from_user_to_to_user is None:
                print """<td></td>"""
            else:
                if username == from_user:
                    print """<td style='text-align: right;color: #CD0000;'>%.2f</td>""" % from_user_to_to_user
                elif username == to_user:
                    print """<td style='text-align: right;color: #008000;'>%.2f</td>""" % from_user_to_to_user
                else:
                    print """<td style='text-align: right;'>%.2f</td>""" % from_user_to_to_user
        print """</tr>"""

    print """</table>"""
    print """</div>"""
    return


def print_logs(filters=[]):
    logs_fields = ('id', 'ts', 'user', 'from_user', 'to_user', 'for_message',
                   'amount')
    where = []
    values = []
    for f in filters:
        field, value = f.split('=')

        # If the filters use short form of the fields set them to the full form.
        if field == 'from':
            field = 'from_user'
        elif field == 'to':
            field = 'to_user'
        elif field == 'for':
            field = 'for_message'

        if field not in logs_fields:
            error('unknown field %s' % field)
        where.append('%s=%%s' % field)
        values.append(value)

    if where:
        where_string = ' AND '.join(where)
        query = 'SELECT * FROM balance_logs WHERE %s ORDER BY ts DESC LIMIT 50' % where_string
        cursor.execute(query, tuple(values))
    else:
        query = 'SELECT * FROM balance_logs ORDER BY ts DESC LIMIT 50'
        cursor.execute(query)

    logs = cursor.fetchall()

    print """<div id='logs-table'>"""
    print """<table>"""
    print """<tr><td style='text-align:right;'>id</td><td>date</td><td>user</td><td>from</td><td>to</td><td>for</td><td style='text-align:right;'>amount</td></tr>"""

    prev_log = None
    for log in logs:
        print """<tr>"""
        print """<td style='text-align:right;'>%s</td>""" % log[0]
        # If the previous log had the same 'for' message and same amount,
        # then don't print the user or timestamp this time.
        if prev_log is None:
            print """<td>%s</td>""" % log[1]
            print """<td>%s</td>""" % log[2]
        elif (prev_log[5] == log[5] and
              prev_log[6] == log[6]):
            print """<td></td>"""
            print """<td></td>"""
        else:
            print """<td>%s</td>""" % log[1]
            print """<td>%s</td>""" % log[2]
        print """<td>%s</td>""" % log[3]
        print """<td>%s</td>""" % log[4]
        print """<td>%s</td>""" % log[5]
        if log[6] > 0:
            print """<td style='text-align: right;'>+%.2f</td>""" % log[6]
        else:
            print """<td style='text-align: right;'>%.2f</td>""" % log[6]
        print """</tr>"""
        prev_log = log

    print """</table>"""
    print """</div>"""
    return


def print_form():
    print """
    <div style='margin-top: 15px;'>
        <input type='text' id='command-box' /> [Enter to submit]
        <br />
        <div id='status'></div>
    </div>
    """
    return


def print_examples():
    print """
    <h1>man</h1>
    Commands:
    <br />
    <code>[USER]+ owes [USER]+ ... [+/-]NUM/EXPR for REASON</code>
    <br />
    <br />
    <code>USER paysoff USER</code>
    <br />
    <br />
    <code>undo [LOG_ID]+</code>
    <br />
    <br />
    <code>edit LOG_ID as REASON</code>
    <br />
    <br />
    <code>filter [FIELD=VALUE]+</code>
    <br />
    <br />
    <code>add_user [USER]+</code> (admin-only)
    <br />
    <br />
    <code>delete [LOG_ID]+</code> (admin-only)
    <br />
    <br />
    <code>remove_user [USER]+</code> (admin-only)
    <br />
    <br />

    <h1>Examples</h1>
    szbokhar owes mtahmed $10 more:
    <br />
    <code>szbokhar owes mtahmed 10</code>
    <br />
    or
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
    Note that the following method clears any debt between the two users and logs
    the transaction
    <br />
    <code>szbokhar paysoff mtahmed</code>
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
    <br />
    <br />
    The amount can be a mathematical expression WITHOUT any spaces:
    <br />
    So for example mtahmed pays $45 for pizza and there are 5 people
    who ate the pizza:
    <br />
    <code>all owes mtahmed +(45/5) for pizza</code>
    <br />
    <code>a3 owes mtahmed +(14*3) for 3 months of internet</code>
    <br />
    <br />
    You can undo a transaction using the undo command. Note that this will
    still log your undo with the for message "UNDO [id]+".
    <br />
    <code>undo 3 4 5</code>
    <br />
    <br />
    You can modify the reason for a transaction if there is a mistake
    (i.e. it's comment) using the 'edit' command. Everything after 'as' is
    considered part of the new comment.
    <br />
    <code>edit 3 as pizza</code>
    <br />
    <br />
    You can filter logs using the filter command and supplying field=value pairs
    where field is one of the headings of the log table. For example if I want
    to see why I owe my4li the amount that I owe him, I can do the following:
    <br />
    <code>filter from=mtahmed to=my4li</code>
    """
    return


def print_body_head():
    print """
<!DOCTYPE HTML>

<html>

<head>
<title>Balance | Muhammad Tauqir Ahmad</title>
<script src='https://ajax.googleapis.com/ajax/libs/jquery/1.4/jquery.min.js'></script>
<script src='https://ajax.googleapis.com/ajax/libs/jqueryui/1.8/jquery-ui.min.js'></script>
<script src='https://csclub.uwaterloo.ca/~mtahmed/balance/commands.js'></script>
<link rel='stylesheet' type='text/css' href='https://csclub.uwaterloo.ca/~mtahmed/css/style-main.css' />
<link rel='stylesheet' type='text/css' href='https://csclub.uwaterloo.ca/~mtahmed/balance/style.css' />

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
        error("permission denied for user: %s" % username)
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

    command_split = [s.strip() for s in command_split]

    # If there's no command...
    if command_split[0] == '':
        print_body_head()
        print """<h1>Balance</h1>"""
        print_balance()
        print_form()
        print """<h1>Logs</h1>"""
        print_logs()
        print_examples()
        print_body_foot()
    elif command_split[0] == 'print_balance':
        print_balance()
    elif command_split[0] == 'print_logs':
        print_logs()
    elif command_split[0] == 'add_user':
        if username not in settings.admin_users:
            error("only admin users can add users.")
        add_list = command_split[1:]
        for user in add_list:
            add_user(user)
    elif command_split[0] == 'delete':
        if username not in settings.admin_users:
            error("only admin users can delete records")
        for record_id in command_split[1:]:
            undo(int(record_id), delete=True)
    elif command_split[0] == 'remove_user':
        if username not in settings.admin_users:
            error("only admin users can remove users")
        for user in command_split[1:]:
            remove_user(user)
    elif command_split[0] == 'undo':
        for record_id in command_split[1:]:
            undo(int(record_id))
    elif command_split[0] == 'edit':
        edit_comment(int(command_split[1]), ' '.join(command_split[3:]))
    elif command_split[1] == 'paysoff':
        user1 = resolve_prefix(command_split[0])
        user2 = resolve_prefix(command_split[2])
        owed1to2 = get_balance(user1, user2)
        owed2to1 = get_balance(user2, user1)
        if owed1to2 == 0:
            if owed2to1 == 0:
                error("there is no owed money between these two users")
            log(user2, user1, "payoff", owed2to1 * -1)
            update_balance(user2, user1, '0', false)
        elif owed2to1 == 0:
            log(user1, user2, "payoff", owed1to2 * -1)
            update_balance(user1, user2, '0', false)
    elif 'owes' in command_split:
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
        for from_user in from_list:
            for to_user in to_list:
                update_balance(from_user, to_user, for_message, amount_str)
    elif command_split[0] == 'filter':
        if len(command_split) > 1:
            print_logs(command_split[1:])
        else:
            print_logs()
    else:
        error("unknown command: %s" % command_str)
