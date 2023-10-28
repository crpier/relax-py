#! /bin/bash

status=0

echo "black:"
if ! black relax --check; then
  status=1
fi
echo -e "---------\n"

echo "isort:"
if ! isort relax --check-only; then
  status=1
fi
echo -e "---------\n"

echo "ruff:"
if ! ruff relax; then
  status=1
fi
echo -e "---------\n"

echo "mypy:"
if ! mypy relax; then
  status=1
fi

exit $status
