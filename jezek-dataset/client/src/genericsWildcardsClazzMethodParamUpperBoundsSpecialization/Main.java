package genericsWildcardsClazzMethodParamUpperBoundsSpecialization;

import java.util.ArrayList;

import testing_lib.genericsWildcardsClazzMethodParamUpperBoundsSpecialization.GenericsWildcardsClazzMethodParamUpperBoundsSpecialization;

public class Main extends GenericsWildcardsClazzMethodParamUpperBoundsSpecialization {

	public static void main(String[] args) {
		GenericsWildcardsClazzMethodParamUpperBoundsSpecialization constr = new GenericsWildcardsClazzMethodParamUpperBoundsSpecialization();
		
		ArrayList<Number> param1 = new ArrayList<Number>();
		constr.method1(param1);
		
	}

	@Override
	public void method1(ArrayList<? extends Number> param1) {

	}
}
