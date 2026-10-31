from django.db import migrations


LESSONS = [
    ('Python', 'python', 'NameError and variable scope', 'A NameError means Python cannot find a name when that line runs. Check spelling, assignment order, and scope.', 'print(total_price)', 'NameError: name total_price is not defined', 'price = 4\nquantity = 3\ntotal_price = price * quantity\nprint(total_price)', 'Assign the name before using it, and use one spelling consistently.', 'What does NameError usually mean?', 'A name was used before it was defined, or its spelling/scope is wrong.'),
    ('Java', 'java', 'NullPointerException', 'A NullPointerException occurs when code uses a reference whose value is null.', 'String name = null;\nSystem.out.println(name.length());', 'NullPointerException', 'String name = "Ada";\nSystem.out.println(name.length());', 'Initialize the reference or check it for null before calling methods.', 'What should you check before calling a method on an object reference?', 'That it is not null.'),
    ('JavaScript', 'javascript', 'Undefined values', 'JavaScript returns undefined when a property or variable has no assigned value. Check the data shape and initialization.', 'const user = {};\nconsole.log(user.name.toUpperCase());', 'TypeError: Cannot read properties of undefined', 'const user = { name: "Ada" };\nconsole.log(user.name.toUpperCase());', 'Validate required fields before using methods on them.', 'What does a missing object property return?', 'undefined.'),
    ('Django', 'django', 'Django URL routing', 'Django checks urlpatterns in order. A route that does not match produces a 404 response.', "path('reports/', views.report)", '404 Not Found for /report/', "path('report/', views.report)", 'Compare the requested path with the route and include the correct trailing slash.', 'Where do you define URL patterns?', 'In urlpatterns, usually in a urls.py module.'),
    ('React', 'react', 'React state updates', 'React renders from state. Mutating an existing object can leave React unaware that the value changed.', 'items.push(newItem);\nsetItems(items);', 'UI may not update after mutation', 'setItems(items => [...items, newItem]);', 'Create a new array or object when updating state.', 'Why use a new array when updating React state?', 'A new reference lets React detect the update.'),
    ('Git', 'git', 'Recovering from an uncommitted change', 'Git status shows which tracked or untracked files differ from the last commit.', 'git status', 'Working tree changes are not committed', 'git add file.py\ngit commit -m "Describe change"', 'Review the diff before staging, then commit only intended changes.', 'Which command shows changed files?', 'git status.'),
    ('Linux', 'linux', 'Permission denied', 'The operating system denied access because the current user lacks the required file or execute permission.', 'cat /root/private.txt', 'Permission denied', 'ls -l /path/to/file', 'Inspect ownership and permissions, then request or grant only the access needed.', 'Which command displays file permissions?', 'ls -l.'),
    ('Databases', 'databases', 'Unique constraint violations', 'A unique constraint prevents duplicate values in a column or column group.', 'INSERT INTO users(email) VALUES (\'ada@example.test\');', 'UNIQUE constraint failed: users.email', 'SELECT email FROM users WHERE email = \'ada@example.test\';', 'Check for an existing record and handle conflicts in the application.', 'What does a unique constraint guarantee?', 'That constrained values are not duplicated.'),
    ('Debugging', 'debugging', 'Read a traceback from the bottom up', 'The last traceback line names the exception. Frames above it show the call path that led to the failing line.', 'result = values[4]', 'IndexError: list index out of range', 'if len(values) > 4:\n    result = values[4]', 'Start at the exception and inspect the relevant frame and inputs.', 'Which traceback part usually names the exception?', 'The final line.'),
    ('Testing', 'debugging', 'Write a focused regression test', 'A regression test captures the behavior that failed so a future change can detect the same problem.', 'def divide(a, b): return a / b', 'ZeroDivisionError for b = 0', 'def test_zero_divisor_is_rejected():\n    with pytest.raises(ZeroDivisionError):\n        divide(1, 0)', 'Use a small test that reproduces the failure and asserts the intended behavior.', 'What should a regression test reproduce?', 'The previously failing behavior.'),
]


def seed_lessons(apps, schema_editor):
    Topic = apps.get_model('learning', 'LearningTopic')
    for order, (title, category, description, explanation, buggy, error, corrected, correction, question, answer) in enumerate(LESSONS, 1):
        Topic.objects.get_or_create(title=title, defaults={
            'category': category, 'description': description, 'explanation': explanation,
            'buggy_code': buggy, 'expected_error': error, 'corrected_code': corrected,
            'correction_explanation': correction, 'practice_question': question,
            'practice_answer': answer, 'order': order,
        })


class Migration(migrations.Migration):
    dependencies = [('learning', '0001_initial')]
    operations = [migrations.RunPython(seed_lessons, migrations.RunPython.noop)]
