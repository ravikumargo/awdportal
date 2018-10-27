// Custom JS for ATP

// Global variables
var reloadTimer = 0;
var autosaveTimer = 0;
var isDirty = false;

function autoReload() {
    if (isDirty !== true) {
        var scroll = $(window).scrollTop();
        var urlSplit = window.location.href.split('?');
        var reloadUrl = urlSplit[0] + '?';

        if (urlSplit.length > 1) {
            var queryString = urlSplit[1].replace(/scroll=\d+&?/g, '');
            if (queryString != '') {
                queryString += '&';
            }
            reloadUrl += queryString;
        }
        reloadUrl += 'scroll=' + scroll;

        window.location.href = reloadUrl;
    }
}

function getUrlParameter(sParam)
{
    var sPageURL = window.location.search.substring(1);
    var sURLVariables = sPageURL.split('&');
    for (var i = 0; i < sURLVariables.length; i++) 
    {
        var sParameterName = sURLVariables[i].split('=');
        if (sParameterName[0] == sParam) 
        {
            return sParameterName[1];
        }
    }

    return -1;
} 

// jQuery code to get CSRF token
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function cleanNumberInputs() {
    var inputs = $(".number-input");

    for (var i = 0; i < inputs.length; i++) {
        var re = new RegExp("[,$]", "g");
        value = $(inputs[i]).val().replace(re, "");
        $(inputs[i]).val(value);
    }
}

function submitPOSTSectionForm(form) {
    cleanNumberInputs();
    var csrftoken = getCookie('csrftoken');
    $('<input />').attr('type', 'hidden')
      .attr('name', "csrfmiddlewaretoken")
      .attr('value', csrftoken)
      .appendTo(form);
    isDirty = false;
    form.submit();
}

function setInputHandler(input) {
    if ($(input).hasClass("datePicker")) {
        $(input).datepicker()
            .on("changeDate", function(e){
                autosave(this);
            });
    } else {
        $(input).change(function() {
            autosave(this);
        });
    }
}

function setInputHandlers() {
    var formInputs = $("#section-form input, #section-form select, #section-form textarea");
    $.each(formInputs, function(index, value) {
        setInputHandler(this);
    });

    $("#submit-and-send").click(function() {
        $("#id_move_to_next_step").val("True");
        submitPOSTSectionForm($("#section-form"));
    });

    $("#submit-and-dual-send").click(function() {
        $("#id_move_to_multiple_steps").val("True");
        submitPOSTSectionForm($("#section-form"));
    });

    $("#submit-and-close").click(function() {
        $("#id_close_award").val("True");
        submitPOSTSectionForm($("#section-form"));
    });

    $("#save-and-return").click(function() {
        $("#id_return_to_parent").val("True");
        submitPOSTSectionForm($("#section-form"));
    });

    $(".select2").not(".award-manager-select").select2();
    $(".award-manager-select").select2({minimumInputLength:2});
}

function updateAutosaveMessage(showId) {
    $(".autosave-message").hide();

    if (showId == "saved") {
        var timeStamp = new Date($.now());
        $("#autosave-saved strong").text("Saved at " + timeStamp.toLocaleString());
        $("#autosave-saved").show();
    } else {
        $("#autosave-" + showId).show();
    }
}

function submitAJAXSectionForm(changedInput) {
    $(".datePicker").datepicker("hide");
    cleanNumberInputs();

    var form = $(changedInput.form);

    var csrftoken = getCookie('csrftoken');
    
    $('<input />').attr('type', 'hidden')
      .attr('name', "csrfmiddlewaretoken")
      .attr('value', csrftoken)
      .appendTo(form);

    updateAutosaveMessage("saving");
    
    $.ajax({
        type: form.attr('method'),
        url: form.attr('action'),
        data: form.serialize(),
    }).done(function (data) {
            var form = $(changedInput.form)[0];
            $(form).replaceWith(data);

            if ($("[id^=error]").length > 0 || $(".alert.alert-block.alert-danger").length > 0) {
                updateAutosaveMessage("form-error");
            } else {
                isDirty = false;
                updateAutosaveMessage("saved");
            }

            setInputHandlers();
            $("form").submit(function() {
                submitPOSTSectionForm(this);
            });
    }).fail(function(data) {
        updateAutosaveMessage("ajax-error");
    });

    return false;
}

function autosave(changedInput) {
    isDirty = true;
    updateAutosaveMessage("pending");

    if (autosaveTimer) {
        clearTimeout(autosaveTimer);
    }
    autosaveTimer = setTimeout(function() {
        submitAJAXSectionForm(changedInput);
    }, 300000);
}

function closeFormWarning() {
    if (isDirty) {
        return "You have unsaved changes on this page. If you continue, your changes will not be saved.";
    }
}

function getAwardNumber() {
    var agency_id = $('#id_agency_name').val();
    var award_template_id = $('#id_award_template').val();
    var org_id = $('#id_department_name').val();
    var prime_sponsor_id = $('#id_who_is_prime').val();  

    if (agency_id != '' && award_template_id != '' && org_id != '') {
        var confirm_message = "Are you sure you wish to request an Award Number?  Once an Award Number is assigned, requesting a new one will make the old number unusable."
        BootstrapDialog.show({
            title: 'Award Number Retrieval Confirmation',
            message: confirm_message,
            closable: false,
            buttons: [{
                label: 'Cancel',
                action: function(dialog) {
                    dialog.close();
                }
            }, {
                label: 'OK',
                cssClass: 'btn-primary',
                action: function(dialog) {
                    submitAwardNumberRequest(agency_id, award_template_id, org_id, prime_sponsor_id);
                    dialog.close();
                }
            }]
        });
    } else {
        BootstrapDialog.alert({
            type: BootstrapDialog.TYPE_DANGER,
            title: "Warning",
            message: "In order to request an Award Number, you must provide Agency Name, Award Template, Department Code & Name and, optionally, Who is Prime"
        });
    }
}

function submitAwardNumberRequest(agency_id, award_template_id, org_id, prime_sponsor_id) {
    var csrftoken = getCookie('csrftoken');
    var data = {agency_id: agency_id, award_template_id: award_template_id, org_id: org_id, prime_sponsor_id: prime_sponsor_id, csrfmiddlewaretoken: csrftoken}

    $.ajax({
        type: 'post',
        url: 'get-award-number-ajax/',
        data: data
    }).done(function(data){
        if (data.award_number != null && data.award_number != '') {
            $('#id_award_number').val(data.award_number);
            BootstrapDialog.alert({
                title: "Award Number Retrieval Success",
                message: "Successfully retrieved Award Number '" + data.award_number + "' from EAS.",
                type: BootstrapDialog.TYPE_SUCCESS
            });
        } else {
            BootstrapDialog.alert({
                title: "Award Number Retrieval Error",
                message: data.error,
                type: BootstrapDialog.TYPE_DANGER
            });
        }
    }).fail(function(data) {
        BootstrapDialog.alert({
            title: "Award Number Retrieval Error",
            message: "Error getting Award Number",
            type: BootstrapDialog.TYPE_DANGER
        });
    });
}