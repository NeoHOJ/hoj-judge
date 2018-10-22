-- phpMyAdmin SQL Dump
-- version 4.1.6
-- http://www.phpmyadmin.net
--
-- 主機: 127.0.0.1
-- 產生時間： 2016年10月03日 下午18:39
-- 伺服器版本: 5.6.16
-- PHP 版本： 5.5.9


SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;


CREATE TABLE IF NOT EXISTS `log` (
  `log_id` int(255) NOT NULL AUTO_INCREMENT,
  `log_ip` varchar(256) COLLATE utf8_unicode_ci DEFAULT NULL,
  `log_time` datetime DEFAULT NULL,
  `log_event` varchar(256) COLLATE utf8_unicode_ci DEFAULT NULL,
  `log_page` varchar(256) COLLATE utf8_unicode_ci DEFAULT NULL,
  `user_id` int(255) DEFAULT NULL,
  PRIMARY KEY (`log_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE IF NOT EXISTS `problem` (
  `problem_id` int(100) NOT NULL,
  `problem_title` varchar(256) COLLATE utf8_unicode_ci DEFAULT NULL,
  `problem_special` int(32) DEFAULT '0',
  `problem_check` text COLLATE utf8_unicode_ci,
  `problem_testdata` text COLLATE utf8_unicode_ci,
  `problem_start` datetime DEFAULT NULL,
  `problem_end` datetime DEFAULT NULL,
  PRIMARY KEY (`problem_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE IF NOT EXISTS `problem` (
  `problem_id` int(100) NOT NULL,
  `problem_title` varchar(256) COLLATE utf8_unicode_ci DEFAULT NULL,
  `problem_special` int(32) DEFAULT '0',
  `problem_check` text COLLATE utf8_unicode_ci,
  `problem_testdata` text COLLATE utf8_unicode_ci,
  `problem_start` datetime DEFAULT NULL,
  `problem_end` datetime DEFAULT NULL,
  PRIMARY KEY (`problem_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE IF NOT EXISTS `submission` (
  `submission_id` int(255) NOT NULL AUTO_INCREMENT,
  `submission_status` int(32) NOT NULL DEFAULT '0',
  `submission_result` text COLLATE utf8_bin,
  `submission_score` int(32) DEFAULT '0',
  `user_id` int(32) NOT NULL,
  `problem_id` int(32) DEFAULT NULL,
  `contest_id` int(32) NOT NULL DEFAULT '-1',
  `submission_code` text COLLATE utf8_bin,
  `submission_mode` int(32) NOT NULL DEFAULT '0',
  `submission_error` text COLLATE utf8_bin,
  `submission_time` int(64) NOT NULL DEFAULT '0',
  `submission_mem` int(64) NOT NULL DEFAULT '0',
  `submission_len` int(32) NOT NULL DEFAULT '0',
  `submission_date` datetime DEFAULT NULL,
  PRIMARY KEY (`submission_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

CREATE TABLE IF NOT EXISTS `user` (
  `user_id` int(32) NOT NULL AUTO_INCREMENT,
  `user_username` varchar(256) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL,
  `user_password` varchar(256) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL,
  `user_level` int(32) NOT NULL DEFAULT '1',
  `user_name` varchar(256) CHARACTER SET utf8 COLLATE utf8_unicode_ci DEFAULT NULL,
  `user_class` varchar(256) CHARACTER SET utf8 COLLATE utf8_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`user_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

CREATE TABLE IF NOT EXISTS `contest` (
  `contest_id` int(255) NOT NULL AUTO_INCREMENT,
  `contest_title` varchar(256) COLLATE utf8_unicode_ci DEFAULT NULL,
  `contest_description` text COLLATE utf8_unicode_ci,
  `contest_mode` int(11) NOT NULL DEFAULT '1',
  `contest_level` int(32) NOT NULL DEFAULT '1',
  `contest_start` datetime NOT NULL,
  `contest_end` datetime NOT NULL,
  `contest_feedback` int(32) NOT NULL DEFAULT '0',
  `contest_score` int(32) NOT NULL DEFAULT '1',
  `contest_oi` int(32) NOT NULL DEFAULT '1',
  `contest_penalty` int(255) NOT NULL DEFAULT '0',
  `contest_showscoreboard` int(32) NOT NULL DEFAULT '1',
  `contest_open` int(255) NOT NULL DEFAULT '0',
  PRIMARY KEY (`contest_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE IF NOT EXISTS `contest_prob` (
  `id` int(255) NOT NULL AUTO_INCREMENT,
  `contest_id` int(255) NOT NULL,
  `problem_id` int(255) NOT NULL,
  `score` int(255) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

CREATE TABLE IF NOT EXISTS `log` (
  `log_id` int(255) NOT NULL AUTO_INCREMENT,
  `log_ip` varchar(256) COLLATE utf8_unicode_ci DEFAULT NULL,
  `log_time` datetime DEFAULT NULL,
  `log_event` varchar(256) COLLATE utf8_unicode_ci DEFAULT NULL,
  `log_page` varchar(256) COLLATE utf8_unicode_ci DEFAULT NULL,
  `user_id` int(255) DEFAULT NULL,
  PRIMARY KEY (`log_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
