"""
Runner for DockCI migrations
"""
import os
import sys

from importlib import import_module


def main():
    try:
        with open('data/version.txt', 'r') as handle:
            data_version = int(handle.read())

    except FileNotFoundError:
        data_version = -1

    migrations_dir = os.path.dirname(os.path.realpath(__file__))
    migrations_list = sorted(os.listdir(migrations_dir))
    for filename in migrations_list:
        try:
            migration_number = int(filename[0:-3])

        except ValueError:
            continue

        if migration_number <= data_version:
            print("--- Migration %d: Already run" % migration_number)
            continue

        if migration_number == data_version + 1:
            print("--- Migration %d:" % migration_number)
            import_module('.%s' % filename[0:-3], __package__)

            with open('data/version.txt', 'w') as handle:
                handle.write("%d" % migration_number)
                data_version = migration_number

        else:
            print((
                "--- Migration %d: Missing migration. Can't jump from %d"
            ) % (migration_number, data_version))
            sys.exit(1)


if __name__ == '__main__':
    main()
