# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
    config.vm.box = "blinkreaction/boot2docker"

    # Network config & shared folders
    config.vm.network "private_network", ip: "192.168.33.89"
    config.vm.synced_folder ".", "/home/docker/tower", id: "tower"

    # VM definition
    config.vm.provider "virtualbox" do |vb|
        vb.name = "Tower"
        vb.memory = 1024
        vb.cpus = 1
    end

    # Bring up containers
    config.vm.provision "shell", run: "always", inline: "cd /home/docker/tower"

    # Disable guest additions auto update as it won't work on boot2docker, and slows vm boot down boot
    if Vagrant.has_plugin?("vagrant-vbguest")
        config.vbguest.auto_update = false
    end
end
