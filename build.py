"""
Simple static page generator.
Uses jinja2 to compile templates.
Templates should live inside `./templates` and will be compiled in '.'.
"""
import csv
import os
import sys

from jinja2 import Environment, FileSystemLoader
try:
    import watchdog.events
    import watchdog.observers
except ImportError:
    pass

# Any extensions that should be added to Jinja
JINJA_EXTENSIONS = []
try:
    from hamlish_jinja import HamlishExtension
except ImportError:
    pass
else:
    JINJA_EXTENSIONS.append(HamlishExtension)

# Absolute path to project
PROJECT_PATH = os.path.realpath(os.path.dirname(__file__))

# Directory to search for templates
TEMPLATE_DIR = "templates"

# Absolute path to templates
TEMPLATE_PATH = os.path.join(PROJECT_PATH, TEMPLATE_DIR)


def render_template(env, template_name, **kwargs):
    """Compile a template.
    *   env should be a Jinja environment variable indicating where to find the
        templates.
    *   template_name should be the name of the template as it appears inside
        of `./templates`.
    *   kwargs should be a series of key-value pairs. These items will be
        passed to the template to be used as needed.
    """
    relpath = os.path.relpath(template_name, TEMPLATE_PATH)
    name, ext = os.path.splitext(relpath)
    print "Building %s..." % relpath
    template = env.get_template(relpath)
    output_name = '%s.html' % name
    with open(output_name, "w") as f:
        f.write(template.render(**kwargs))


def parse_csv(filename):
    """Read data from a CSV.
    This will return a list of dictionaries, with key-value pairs corresponding
    to each column in the parsed csv.
    """
    with open(filename, 'rb') as f:
        return list(csv.DictReader(f))


# Map of filenames to context generators
# Used to generate contexts for specific templates
CONTEXTS = {}


def context_generator(filename):
    """Register a context generator for the matching filename."""
    def wrapper(func):
        CONTEXTS[filename] = func
        return func
    return wrapper


def should_render(filename):
    """Check if the file should be rendered.
    -   Hidden files will not be rendered.
    -   Files prefixed with an underscore are assumed to be partials and will
        not be rendered.
    -   Directories will not be rendered.
    """
    # Don't render partials or hidden files
    return not (filename.startswith('_')
        or filename.startswith(".")
        or (len(filename.split(".")) == 1))


def find_templates(searchpath):
    """Find all templates in a directory."""
    for root, _, filenames in os.walk(searchpath):
        for filename in filenames:
            if should_render(filename):
                yield os.path.join(root, filename)


def render_templates(env, searchpath):
    """Compile each of the templates."""
    for filename in find_templates(searchpath):
        try:
            context = CONTEXTS[filename]()
        except KeyError:
            context = {}
        render_template(env, filename, **context)


def watch_templates(path, event_handler, poll_frequency=1):
    """Watch a directory for changes.
    -   path is the path to monitor
    -   event_handler is be an event handler which specifies the behavior
    -   poll_frequency is the frequency (measured in seconds) that we poll at
    """
    import time

    # Start watching for any changes
    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, path=path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(poll_frequency)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main(argv):
    env = Environment(loader=FileSystemLoader(searchpath=TEMPLATE_PATH),
                      extensions=JINJA_EXTENSIONS)
    render_templates(env, TEMPLATE_PATH)
    print "Templates built."
    if len(argv) > 1 and argv[1] == '--watch':
        class JinjaEventHandler(watchdog.events.FileSystemEventHandler):
            """
            Naive recompiler.
            Rebuilds all templates if anything changes in /templates.
            """
            def on_modified(self, event):
                super(JinjaEventHandler, self).on_created(event)
                # This is inefficient, but it's not obvious how to see which
                # file changed from the event object we get back. Namely,
                # watchdog seems to only notice .swp files changing, rather
                # than the src files
                if event.src_path.startswith(TEMPLATE_PATH):
                    render_templates(env, TEMPLATE_PATH)
        event_handler = JinjaEventHandler()
        print "Watching '%s' for changes..." % TEMPLATE_PATH
        print "Press Ctrl+C to stop."
        watch_templates(TEMPLATE_PATH, event_handler)
        print "Process killed"
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
