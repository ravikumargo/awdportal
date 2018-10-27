$(document).ready(function() {
    if (disableAutosave) {
        $('#autosave-disabled').show();
        $(".datePicker").datepicker();
        $(".select2").not(".award-manager-select").select2();
        $(".award-manager-select").select2({minimumInputLength:2});

        $("#save-and-return").click(function() {
            $("#id_return_to_parent").val("True");
            submitPOSTSectionForm($("#section-form"));
        });
    } else {
        setInputHandlers();
    }

    $("form").submit(function() {
        submitPOSTSectionForm(this);
    });

    // Always reset the move_to_next_step field to False
    $("#id_move_to_next_step").val("False");
});

window.onbeforeunload = closeFormWarning;
