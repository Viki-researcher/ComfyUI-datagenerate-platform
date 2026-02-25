#!/bin/bash
# 推送到Gitee的脚本

cd /home/admin1/ai02/codeyard/wk_codeyard/Code_backup/ComfulUI

# 添加Gitee远程仓库
git remote add gitee https://gitee.com/akaizi/ComfyUI-datagenerate-platform.git 2>/dev/null || true

# 推送到Gitee
echo "正在推送到Gitee..."
git push -u gitee master
