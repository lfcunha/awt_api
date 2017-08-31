VAGRANTFILE_API_VERSION = "2"
ANSIBLE_TAGS=ENV['ANSIBLE_TAGS']

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  config.vm.box = "bento/ubuntu-16.04"
  config.ssh.insert_key = false
  config.vm.synced_folder "~/developer/swt-api", "/opt/swt/SWT-FSE",
    mount_options: ["dmode=775,fmode=775"],
    disabled: false,
    create: true
  config.vm.synced_folder '.', '/vagrant', disabled: true

  config.ssh.forward_agent = true
  config.hostmanager.enabled = true
  config.hostmanager.manage_host = true

  config.vm.provider :virtualbox do |vb|
    vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
    vb.customize ["setextradata", :id, "VBoxInternal2/SharedFoldersEnableSymlinksCreate//opt/swt", "1"]
  end

  config.vm.define "swt" do |swt|
    swt.vm.network "forwarded_port", guest: 5000, host: 5001 # api from supervisor
    swt.vm.network "forwarded_port", guest: 8000, host: 8003 # api from cli
    #swt.vm.network "forwarded_port", guest: 80, host: 8080 # web
    #swt.vm.network "forwarded_port", guest: 5432, host: 5433 # postgres
    #swt.vm.network "forwarded_port", guest: 5672, host: 5673 # rmq
    #swt.vm.network "forwarded_port", guest: 6379, host: 6380 # redis
    #swt.vm.network "forwarded_port", guest: 28015, host: 28016 # rtdb
    swt.hostmanager.aliases = [
        'swt.example.org',
        'api.swt.example.org',
        'client.swt.example.org',
    ]
  end

  config.vm.provision :ansible do |ansible|
    ansible.verbose = 'v'
    ansible.playbook = "vagrant.yml"
    ansible.extra_vars = "./local_vars.yml"
    ansible.groups = {
        "swt" => ["swt"],
      }
    ansible.vault_password_file = "~/.vault_pass.txt"
    ansible.tags = ANSIBLE_TAGS # run with:  export ANSIBLE_TAGS="tag1,tag2"; vagrant provision swt
  end

end
