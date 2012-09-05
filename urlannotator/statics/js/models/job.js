// Requires Knockout to be imported inside importing script's scope

function alert(screenshot, worker_id, worker_name, title, content, job_id){
  this.screenshot = screenshot;
  this.worker_id = worker_id;
  this.workerName = worker_name;
  this.title = title;
  this.content = content;
  this.job_id = job_id

  this.hasWorker = ko.computed(function(){
    return this.worker_id;
  }, this);
  this.workerURL = ko.computed(function(){
    if (this.hasWorker())
      return '/project/'+this.job_id+'/workers/'+this.worker_id+'/';
    return '';
  }, this);
  this.hasScreenshot = ko.computed(function(){
    return this.screenshot;
  }, this);
}

function job(){
  this.urls_collected = ko.observable();
  this.progress = ko.observable();
  this.hours_spent = ko.observable();
  this.budget = ko.observable();
  this.cost = ko.observable();
  this.no_of_workers = ko.observable();
  this.gather_url = ko.observable();
  this.voting_url = ko.observable();
  this.alerts = ko.observableArray();
}
