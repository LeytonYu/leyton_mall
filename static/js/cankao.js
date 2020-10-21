
$(function(){
	var $slides = $('.slide_pics li');

	//定义有多少张图片，这里有4张
	var len = $slides.length;
	var nowli = 0; //将要运动过来的li，就是你点击想看的图片li,序列号从0开始算起
	var prevli = 0; //当前要离开的li
	var $prev = $('.prev');  //给左边的箭头定义变量
	var $next = $('.next');  //右边的箭头定义变量
	var ismove = false;
	var timer = null; //定义一个定时器的占位符

	//每个li的宽度是760，这里把除了第一个图之外的所有图都放到右边
	$slides.not(':first').css({left:760});

	//
	$slides.each(function(index, el) {
		var $li = $('<li>'); //创建li标签，就是下面的滚动点

		if(index==0) //设定第一个li的样式是高亮的
		{
			$li.addClass('active');
		}

		$li.appendTo($('.points'));  //实现把<li>滚动点附加到页面中
	});


	$points = $('.points li'); //选中4个点

	timer = setInterval(autoplay,4000);//定时器4秒放一次图片，实现幻灯片自动播放


	//实现把鼠标放在幻灯片上时，停止播放，鼠标移开后继续播放
	$('.slide').mouseenter(function() {
		clearInterval(timer); //消除定时器
	});

	$('.slide').mouseleave(function() {
		timer = setInterval(autoplay,4000);
	});


	//幻灯片自动播放，其实就是和右箭头绑定事件一样
	function autoplay(){
		nowli++;
		move();
		$points.eq(nowli).addClass('active').siblings().removeClass('active');
	}


	//在滚动点上绑定事件，使点击滚动点的时候可跳到相应幻灯片
	$points.click(function(event) {
		if(ismove)
		{
			return;
		}


		nowli = $(this).index(); //选取想要移动的图片的索引值


		//消除重复点击选择图片li点时，出现的bug
		if(nowli==prevli)
		{
			return;
		}

		$(this).addClass('active').siblings().removeClass('active'); //选中的点颜色会变化
		move(); //move函数来定义运动，在后面定义的有，就是function move()

	});


	//左箭头绑定事件
	$prev.click(function() {
		if(ismove)
		{
			return;
		}
		nowli--;
		move();
		$points.eq(nowli).addClass('active').siblings().removeClass('active'); //箭头使图片移动的同时，下面的点也要相应移动

	});

	//右箭头绑定事件
	$next.click(function() {
		if(ismove)
		{
			return;
		}
		nowli++;
		move();
		$points.eq(nowli).addClass('active').siblings().removeClass('active');

	});


	//move函数处理所有的运动
	//当快速点击箭头时，会出现一些图片显示的问题，解决方法：可以在所有的animate()前面加上stop()
	//例如：$slides.eq(nowli).stop().animate({left:0},800,'easeOutExpo')
	function move(){

		ismove = true;

		if(nowli<0) //在第一张图片上还想左移的情况
		{
			nowli=len-1;  //让第4张图片从左边过来
			prevli = 0
			$slides.eq(nowli).css({left:-760}); //把第4张图片先放在左边
			$slides.eq(nowli).animate({left:0},800,'easeOutExpo'); //然后放在原先图片1的位置
			$slides.eq(prevli).animate({left:760},800,'easeOutExpo',function(){//原先图片1的位置右移
				ismove = false;
			});
			prevli=nowli;
			return;  //不执行下面的条件判断语句
		}

		//在第4张图片时，还想按右移箭头时
		if(nowli>len-1)
		{
			nowli = 0; //出来的图片应该是第一张图
			prevli = len-1;
			$slides.eq(nowli).css({left:760});
			$slides.eq(nowli).animate({left:0},800,'easeOutExpo');
			$slides.eq(prevli).animate({left:-760},800,'easeOutExpo',function(){
				ismove = false;
			});
			prevli=nowli;
			return;  //return的作用是不执行下面的条件语句
		}


		if(prevli<nowli) //看图片按从小到大顺序的时候，比如从第一个到第二个
		{
			$slides.eq(nowli).css({left:760});	//先把大号的图放右边
			$slides.eq(prevli).animate({left:-760},800,'easeOutExpo');//把小号图左边放
			$slides.eq(nowli).animate({left:0},800,'easeOutExpo',function(){ //再把大号图放在原先小号图的位置
				ismove = false;
			});
			prevli=nowli; //nowli的值一直变的，这里把nowli值赋值给preli

		}

		//从大到小看图片
		else
		{
			$slides.eq(nowli).css({left:-760});
			$slides.eq(prevli).animate({left:760},800,'easeOutExpo');
			$slides.eq(nowli).animate({left:0},800,'easeOutExpo',function(){
				ismove = false;
			});
			prevli=nowli;
		}
	}
})