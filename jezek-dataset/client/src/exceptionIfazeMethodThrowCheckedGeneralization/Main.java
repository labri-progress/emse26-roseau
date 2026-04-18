package exceptionIfazeMethodThrowCheckedGeneralization;

import java.io.FileNotFoundException;

import testing_lib.exceptionIfazeMethodThrowCheckedGeneralization.ExceptionIfazeMethodThrowCheckedGeneralization;

public class Main {

	public static void main(String[] args) {
		ExceptionIfazeMethodThrowCheckedGeneralization constr = new ExceptionIfazeMethodThrowCheckedGeneralization() {
			@Override public void method1() {}
		};
		try {
			constr.method1();
		} catch (FileNotFoundException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
	
}
