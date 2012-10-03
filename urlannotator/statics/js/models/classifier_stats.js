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
    return 100 * this.yesCount() / div;
  }, this);
  this.noPerc = ko.computed(function() {
    div = this.allCount();
    if (div == 0){
      div = 1
    }
    return 100 * this.noCount() / div;
  }, this);
  this.brokenPerc = ko.computed(function() {
    div = this.allCount();
    if (div == 0){
      div = 1
    }
    return 100 * this.brokenCount() / div;
  }, this);
}
