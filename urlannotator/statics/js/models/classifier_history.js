// Requires Knockout to be imported inside importing script's scope

var classifier_history_entry = function(screenshot, url, label, yes_prob, no_prob, broken_prob, finished){
  this.screenshot = screenshot;
  this.url = url;
  this.label = label;
  this.yes_prob = yes_prob;
  this.no_prob = no_prob;
  this.broken_prob = broken_prob;
  this.finished = finished;

  this.probability = ko.computed(function(){
    return this.yes_prob*100 + '% ' + this.no_prob*100 + '% ' + this.broken_prob*100 + '%';
  }, this);
  this.hasScreenshot = ko.computed(function(){
    return this.screenshot && this.screenshot != '';
  }, this);
  this.getLabel = ko.computed(function(){
    if (this.finished)
      return this.label;
    return 'PENDING';
  }, this);
  this.getProbability = ko.computed(function(){
    if (this.finished)
      return this.probability();
    return '-';
  }, this);
};

function classifier_history(){
  this.entries = ko.observableArray();
};

