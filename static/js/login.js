$(function () {

    var error_name = true;
    var error_pwd = true;
    const name_input = document.querySelector("[name='username']");
    const pwd_input = document.querySelector("[name='pwd']");
    const name_err = document.querySelector('#name_err');
    const pwd_err = document.querySelector('#pwd_err');

    function check_name(){
        if ($(name_input).val() == null||$(name_input).val() === "") {
            $(name_err).slideDown("normal");
            error_name = true;
        } else {
            $(name_err).slideUp("normal");
            error_name = false;
        }
    }

    function check_pwd(){
        if ($(pwd_input).val() == null||$(pwd_input).val() === "") {
            $(pwd_err).slideDown("normal");
            error_pwd = true;
        } else {
            $(pwd_err).slideUp("normal");
            error_pwd = false;
        }
    }

    $(name_input).blur(function () {
        check_name();
    });

    $(name_input).focus(function () {
        $(name_err).slideUp('normal')
    });

    $(pwd_input).blur(function () {
        check_pwd();
    });

    $(pwd_input).focus(function () {
        $(pwd_err).slideUp('normal')
    });

    $('form').submit(function () {
        check_name();
        check_pwd();
        return error_name === false && error_pwd === false
    });

});