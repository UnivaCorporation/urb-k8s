Build base docker image:

  make

Provision and start build environment:

  vagrant up

Access build environment

  vagrant ssh

Build project (from inside the guest, after vagrant ssh):

  cd /scratch/urb   # change directory to the project root
  make              # run build
  make test         # run unit tests
  make dist         # create distrubution archive in dist direcotry
  exit              # exit from the build environment

Shutdown the build environment:

  vagrant halt

Completely destroy build environment:

  vagrant destroy

Clean docker image:

  make clean
