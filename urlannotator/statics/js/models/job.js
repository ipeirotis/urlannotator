// Requires Knockout to be imported inside importing script's scope

function worker(){
  this.id = ko.observable();
  this.urls_collected = ko.observable();
  this.name = ko.observable();
  this.hours_spent = ko.observable();
  this.votes_added = ko.observable();
  this.earned = ko.observable();
  this.start_time = ko.observable();
  this.job_id = ko.observable();

  this.worker_url = ko.computed(function(){
    return '/project/' + this.job_id() + '/workers/' + this.id()
  }, this);
}

function vote(){
  this.screenshot = ko.observable();
  this.url = ko.observable();
  this.added_on = ko.observable();
  this.label = ko.observable();
  this.sample_url = ko.observable();
  this.date = ko.observable();
}


function alert_view(screenshot, worker_id, worker_name, title, content, job_id, delta){
  this.screenshot = screenshot;
  this.worker_id = worker_id;
  this.workerName = worker_name;
  this.title = title;
  this.content = content;
  this.job_id = job_id;
  this.delta = delta;

  this.hasWorker = ko.computed(function(){
    return this.worker_id;
  }, this);
  this.workerURL = ko.computed(function(){
    if (this.hasWorker())
      return '/project/'+this.job_id+'/workers/'+this.worker_id;
    return '';
  }, this);
  this.hasScreenshot = ko.computed(function(){
    return this.screenshot;
  }, this);
  this.time_ago = ko.computed(function(){
    var elapsed = this.delta;
    var sPerMinute = 60;
    var sPerHour = sPerMinute * 60;
    var sPerDay = sPerHour * 24;
    var sPerMonth = sPerDay * 30;
    var sPerYear = sPerDay * 365;

    if (elapsed < sPerMinute) {
      val = Math.round(elapsed);
      if (val == 1)
        return 'A second ago';
      else
        return val + ' seconds ago';
    }

    else if (elapsed < sPerHour) {
      val = Math.round(elapsed/sPerMinute);
      if (val == 1)
        return 'A minute ago';
      else
        return val + ' minutes ago';
    }

    else if (elapsed < sPerDay ) {
      val = Math.round(elapsed/sPerHour);
      if (val == 1)
        return  'An hour ago';
      else
        return val + ' hours ago';
    }

    else if (elapsed < sPerMonth) {
      val = Math.round(elapsed/sPerDay);
      if (val == 1)
        return 'A day ago';
      else
        return val + ' days ago';
    }

    else if (elapsed < sPerYear) {
      val = Math.round(elapsed/sPerMonth);
      if (val == 1)
        return 'A month ago';
      else
        return val + ' months ago';
    }

    else {
      val = Math.round(elapsed/sPerYear);
      if (val == 1)
        return 'A year ago';
      else
        return val + ' years ago';
    }
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
  this.top_workers = ko.observableArray();
  this.newest_votes = ko.observableArray();
  this.progress_urls = ko.observable();
  this.progress_votes = ko.observable();
  this.votes_gathered = ko.observable();

  this.hasOwnWorkforceLinks = ko.computed(function(){
    return (this.gather_url() != "") || (this.voting_url() != "");
  }, this);
  this.has_newest_votes = ko.computed(function(){
    return this.newest_votes().length > 0
  }, this);
  this.has_top_workers = ko.computed(function(){
    return this.top_workers().length > 0
  }, this);
}
