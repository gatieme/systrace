#!/bin/sh

rm /data/mem_stat.txt

while [ 1 ]; do
	date >> /data/mem_stat.txt
	echo "cat /proc/meminfo"	>> /data/mem_stat.txt
	cat /proc/meminfo	>> /data/mem_stat.txt
	echo "cat /proc/memview"	>> /data/mem_stat.txt
	cat /proc/memview	>> /data/mem_stat.txt
	echo "cat /proc/buddyinfo"	>> /data/mem_stat.txt
	cat /proc/buddyinfo	>> /data/mem_stat.txt
	echo "cat /dev/memcg/memory.zswapd_presure_show"	>> /data/mem_stat.txt
	cat /dev/memcg/memory.zswapd_presure_show	>> /data/mem_stat.txt
	echo "cat /proc/devhost/root/dmaheap_pagepool"	>> /data/mem_stat.txt
	cat /proc/devhost/root/dmaheap_pagepool	>> /data/mem_stat.txt
	echo "cat /proc/gpu_memory"	>> /data/mem_stat.txt
	cat /proc/gpu_memory	>> /data/mem_stat.txt
	echo "cat /proc/devhost/root/buddyinfo"	>> /data/mem_stat.txt
	cat /proc/devhost/root/buddyinfo	>> /data/mem_stat.txt
	echo " cat /proc/devhost/root/iofast"	>> /data/mem_stat.txt
	cat /proc/devhost/root/iofast	>> /data/mem_stat.txt
	echo " cat /proc/devhost/root/shrinkers"	>> /data/mem_stat.txt
	cat /proc/devhost/root/shrinkers	>> /data/mem_stat.txt
	sleep 5
done
