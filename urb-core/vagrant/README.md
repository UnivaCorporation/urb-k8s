Following are the instructions for building urb-core project as a separate component.
External projects implementing scheduler adapter interface can use urb-core as a subproject
in which case build instructions from those projects might be used instead.

## Build base docker image:

  `cd vagrant; make`

## Provision and start build environment:

  `vagrant up --provider=docker`

## Access build environment:

  `vagrant ssh`

## Build project (from inside the guest, after `vagrant ssh`):

- change directory to the project root:

  `cd /scratch/urb`

- run build:

  `make`

- run unit tests:

  `make test`

- create distrubution archive in `dist` direcotry:

  `make dist`

- exit from the build environment:

  `exit`

## Shutdown the build environment:

  `vagrant halt`

## Completely destroy build environment:

  `vagrant destroy`

## Clean docker image:

  `make clean`
