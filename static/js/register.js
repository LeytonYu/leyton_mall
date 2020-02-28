$(function () {

    var error_name = true;
    var error_password = true;
    var error_check_password = true;
    var error_email = true;
    var error_check = false;


    $('#user_name').blur(function () {
        check_user_name();
    });

    $('#pwd').blur(function () {
        check_pwd();
    });

    $('#cpwd').blur(function () {
        check_cpwd();
    });

    $('#email').blur(function () {
        check_email();
    });

    $('#email').focus(function () {
        $('#emali_err').slideUp("normal")
    });

    $('#user_name').focus(function () {
        $('#name').slideUp("normal")
    });

    $('#pwd').focus(function () {
        $('#pwd_err').slideUp("normal")
    });

    $('#cpwd').focus(function () {
        $('#cpwd_err').slideUp("normal")
    });

    $('#allow').click(function () {
        if ($(this).is(':checked')) {
            error_check = false;
            $('#allow_err').slideUp("normal");
        } else {
            error_check = true;
            $('#allow_err').slideDown("normal");
        }
    });

    function check_user_name() {
        var user_name = $('#user_name').val();
        if (user_name == null || user_name === "") {
            $('#name_err').find("label").text("用户名不能为空").css("color", "lightpink");
            $('#name_err').slideDown('normal');
            error_name = true;
        } else {
            $.ajax({
                url: '/user/name_check/',
                type: 'post',
                dataType: 'json',
                traditional: true,//这个参数必须添加，采用传统方式转换
                data: {name: user_name},
                async: false,
                success: function (result) {
                    if (result.resultCode == 0) {
                        $('#name_err').slideUp('normal');
                        error_name = false;
                    } else {
                        $('#name_err').slideDown('normal');
                        error_name = true;
                    }
                }
            });
        }
    }

    function check_pwd() {
        var len = $('#pwd').val().length;
        if (len < 8 || len > 20) {
            $('#pwd_err').slideDown('normal');
            error_password = true;
        } else {
            $('#pwd_err').slideUp('normal');
            error_password = false;
        }
    }


    function check_cpwd() {
        var pass = $('#pwd').val();
        var cpass = $('#cpwd').val();

        if (pass !== cpass) {
            $('#cpwd_err').slideDown('normal');
            error_check_password = true;
        } else {
            $('#cpwd_err').slideUp('normal');
            error_check_password = false;
        }

    }

    function check_email() {
        var re = /^[a-zA-Z0-9][\w\.\-]*@[a-zA-Z0-9\-]+(\.[a-z]{2,5}){1,2}$/;

        if (re.test($('#email').val())) {
            $.ajax({
                url: '/user/email_check/',
                type: 'post',
                dataType: 'json',
                traditional: true,//这个参数必须添加，采用传统方式转换
                data: {email: $('#email').val()},
                async: false,
                success: function (result) {
                    if (result.resultCode == 0) {
                        $('#emali_err').slideUp("normal");
                        error_email = false;
                    } else {
                        $('#emali_err').find("label").text("邮箱重复了").css("color", "lightpink");
                        $('#emali_err').slideDown("normal");
                        error_check_password = true;
                    }
                }
            });

        } else {
            $('#emali_err').find("label").text("邮箱格式不正确").css("color", "lightpink");
            $('#emali_err').slideDown("normal");
            error_check_password = true;

        }

    }


    $('form').submit(function () {
        return error_name === false && error_password === false && error_check_password === false && error_email === false && error_check === false
    });
});