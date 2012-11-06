// Requires Knockout to be imported inside importing script's scope

function classifier_stats(){
  this.yesCount = ko.observable();
  this.brokenCount = ko.observable();
  this.noCount = ko.observable();

  this.allCount = ko.computed(function() {
    return this.yesCount() + this.noCount() + this.brokenCount();
  }, this);
  this.yesPerc = ko.computed(function(){
    div = this.allCount();
    if (div == 0){
      div = 1
    }
    return Math.round(100 * this.yesCount() / div, 2);
  }, this);
  this.noPerc = ko.computed(function() {
    div = this.allCount();
    if (div == 0){
      div = 1
    }
    return Math.round(100 * this.noCount() / div, 2);
  }, this);
  this.brokenPerc = ko.computed(function() {
    div = this.allCount();
    if (div == 0){
      div = 1
    }
    return Math.round(100 * this.brokenCount() / div, 2);
  }, this);
}
