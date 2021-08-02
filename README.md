# spaces-record
一个简单的推特空间的自动录播，防错设置较少，且未经过长时间测试，可以临时用用，如有需要，可以自行修改

#### 文件介绍
文件名|描述
:---|:----
twitter_spaces.py|主程序源码
twitter_spaces.json|配置文件
twitter_spaces.exe|打包好的可执行文件，windows系统下如未配置过python运行环境或三方库不全的可以使用

#### 配置
key           |是否必选|  描述
:-------      |:----: | :----
user_id       |  可选  |  用户rest_id，注意不是screen_name，默认为1130858667547299841，即用户kaguramea_vov的id
save_path     |  可选  |  文件存储路径，默认为主程序文件夹下的"./rec/{user_id}"
cookie        |  必选  |  账号cookie，因推特必须登录使用，无cookie无法运行
invl_twit     |  可选  |  获取推文间隔，单位为秒，默认60
invl_twit_err |  可选  |  获取推文失败时，重试间隔，单位为秒，默认10
times_aac_err |  可选  |  获取aac片段失败时，最大重试次数，不建议太多，以防止错过后面的片段，默认5